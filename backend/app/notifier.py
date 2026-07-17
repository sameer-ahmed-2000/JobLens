import os
import sys
import json
import logging
import time
import signal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
import httpx
import redis

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.repositories.uow import UnitOfWork
from app.models.orm import UserORM, JobMatchORM, JobORM
from app.services.llm_router import llm_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s [cid=%(correlation_id)s] - %(message)s"
)
logger = logging.getLogger("notifier")

# Install the filter on the root logger so all handlers inherit it.
# This must happen after basicConfig() so the handler exists.
from app.log_context import CorrelationIdFilter, set_correlation_id
logging.getLogger().addFilter(CorrelationIdFilter())

class Notifier:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="NotifierWorker")

    def connect_redis(self):
        try:
            self.redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"Notifier connected to Redis at {settings.redis_url}")
            return True
        except Exception as e:
            logger.error(f"Notifier failed to connect to Redis at {settings.redis_url}: {e}")
            return False

    def handle_message_async(self, message):
        """Concurrently handles a pubsub message."""
        try:
            self.process_message(message)
        except Exception as e:
            logger.error(f"Error handling message concurrently: {e}", exc_info=True)

    def process_message(self, message):
        channel = message.get("channel")
        data_str = message.get("data")
        if not channel or not data_str:
            return

        # 1. Parse user_id from channel (job_events:{user_id})
        parts = channel.split(":")
        if len(parts) < 2:
            logger.warning(f"Invalid channel pattern: {channel}")
            return
        user_id = parts[1]

        # 2. Parse event payload
        try:
            event = json.loads(data_str)
        except Exception as e:
            logger.error(f"Failed to parse event JSON data: {e}")
            return

        if event.get("type") != "new_match":
            logger.debug(f"Ignoring non-new_match event type: {event.get('type')}")
            return

        # 3. Set correlation ID from the payload so all subsequent log lines in
        #    this thread carry the originating job_id — closing the cross-process
        #    tracing gap that contextvars alone cannot bridge.
        set_correlation_id(event.get("job_id", "-"))

        score = event.get("score")
        job_match_id = event.get("job_match_id")
        title = event.get("title")
        company = event.get("company")
        url = event.get("url")

        if score is None or not job_match_id:
            logger.warning(f"Event missing required fields: score={score}, job_match_id={job_match_id}")
            return

        # 3. Retrieve user profile
        with UnitOfWork() as uow:
            user = uow.session.query(UserORM).filter(UserORM.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found in DB.")
                return
            
            # Read preferences under lock/transaction
            email = user.email
            whatsapp_number = user.whatsapp_number
            notify_threshold = user.notify_threshold
            user_name = user.name

        # 4. Check against notify threshold
        if score < notify_threshold:
            logger.info(f"Score {score} is below user {user_id} notify_threshold {notify_threshold}. Skipping alert.")
            return

        # 5. Deduplication check FIRST to prevent hot-retries from burning rate limits
        dedup_key = f"notified:{user_id}"
        try:
            added = self.redis_client.sadd(dedup_key, job_match_id)
            if added == 1:
                # Expire notified set in 7 days
                self.redis_client.expire(dedup_key, 7 * 24 * 3600)
            else:
                logger.info(f"Match {job_match_id} already notified for user {user_id}. Skipping duplicate alert.")
                return
        except Exception as e:
            logger.error(f"Deduplication redis check failed: {e}")
            # In case of Redis errors, do not fail silently, but proceed to ensure alert is sent.

        # 6. Rate Limit check SECOND
        rate_key = f"notify:rate:{user_id}"
        try:
            count = self.redis_client.incr(rate_key)
            if count == 1:
                self.redis_client.expire(rate_key, 3600)
            if count > settings.max_notifs_per_hour:
                logger.warning(f"Rate limit exceeded for user {user_id} ({count} > {settings.max_notifs_per_hour}/hr). Discarding alert.")
                return
        except Exception as e:
            logger.error(f"Rate limiting redis check failed: {e}")

        # 7. Fetch or generate rationale teaser
        rationale = None
        with UnitOfWork() as uow:
            match = uow.session.query(JobMatchORM).filter(JobMatchORM.id == job_match_id).first()
            if match:
                rationale = match.rationale
                if not rationale:
                    # Generate rationale teaser synchronously in this thread
                    job = uow.session.query(JobORM).filter(JobORM.id == match.job_id).first()
                    if job:
                        # Call LLM
                        active_resume = uow.resumes.get_active(user_id)
                        if active_resume:
                            skills_source = active_resume.get("skills") or active_resume.get("parsed_skills") or []
                            resume_skills = ", ".join(skills_source)
                        else:
                            from app.services.resume_index import resume_index
                            resume_data = resume_index.get_resume_data() or {}
                            resume_skills = ", ".join(resume_data.get("skills", []))
                        
                        prompt = f"""You are an AI career advisor.
Resume Skills: {resume_skills}
Job Title: {job.title} at {job.company.name if job.company else 'Unknown Company'}
Job Description: {job.description[:400]}

Write ONE sentence.
Maximum 25 words.
Mention only overlapping skills.
Do not invent experience."""
                        try:
                            logger.info(f"Generating rationale teaser for user {user_id} and job {job.id}")
                            rationale = llm_router.generate(prompt=prompt)
                            match.rationale = rationale
                            uow.commit()
                        except Exception as ex:
                            logger.error(f"Failed to generate lazy rationale: {ex}")
                            rationale = "Fits your background skills."

        if not rationale:
            rationale = "Fits your background skills."

        # 8. Send Notification with try/except exception isolation
        # Formulate message template
        subject = f"JobLens Match Alert: {title} at {company}"
        message = (
            f"Hi {user_name},\n\n"
            f"We found a new job match with a score of {int(score * 100)}%!\n\n"
            f"Position: {title}\n"
            f"Company: {company}\n"
            f"Why it fits: {rationale}\n\n"
            f"View Match: {settings.frontend_url}/?match={job_match_id}\n\n"
            f"Best,\nJobLens Team"
        )

        try:
            if whatsapp_number:
                success = self.send_whatsapp(whatsapp_number, message)
                if not success:
                    logger.warning("WhatsApp failed, falling back to email")
                    self.send_email(email, subject, message)
            else:
                self.send_email(email, subject, message)
        except Exception as e:
            logger.error(f"Failed to dispatch alert to user {user_id}: {e}", exc_info=True)

    def send_whatsapp(self, number: str, message: str) -> bool:
        token = settings.whatsapp_api_token
        phone_id = settings.whatsapp_phone_number_id
        
        if not token or not phone_id:
            logger.info(f"[WHATSAPP MOCK] Send to {number}:\n{message}\n")
            return True
            
        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=10.0)
            if resp.status_code in (200, 201):
                logger.info(f"Sent WhatsApp message to {number}")
                return True
            else:
                logger.error(f"WhatsApp API error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed calling WhatsApp API: {e}")
            return False

    def send_email(self, address: str, subject: str, body: str) -> bool:
        host = settings.smtp_host
        port = settings.smtp_port
        user = settings.smtp_username
        password = settings.smtp_password
        from_addr = settings.smtp_from
        
        if not host:
            logger.info(f"[EMAIL MOCK] Send to {address}:\nSubject: {subject}\nBody: {body}\n")
            return True
            
        try:
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = address
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(host, port, timeout=5.0) as server:
                if user and password:
                    server.starttls()
                    server.login(user, password)
                server.send_message(msg)
            logger.info(f"Sent email alert to {address}")
            return True
        except Exception as e:
            logger.warning(f"SMTP failed, falling back to mock logs (Error: {e})")
            logger.info(f"[EMAIL MOCK] Send to {address}:\nSubject: {subject}\nBody: {body}\n")
            return True

    def start(self):
        self.running = True
        logger.info("Notifier process loop started.")
        
        while self.running:
            if not self.redis_client:
                if not self.connect_redis():
                    time.sleep(5)
                    continue
            
            try:
                self.pubsub = self.redis_client.pubsub()
                self.pubsub.psubscribe("job_events:*")
                logger.info("Notifier subscribed to Redis channel pattern 'job_events:*'")
                
                for message in self.pubsub.listen():
                    if not self.running:
                        break
                    if message["type"] == "pmessage":
                        # Concurrently handle the message using the ThreadPoolExecutor
                        self.executor.submit(self.handle_message_async, message)
            except redis.exceptions.ConnectionError:
                logger.error("Redis connection lost in Notifier. Reconnecting in 5 seconds...")
                self.redis_client = None
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in Notifier main loop: {e}", exc_info=True)
                time.sleep(5)

    def stop(self):
        self.running = False
        if self.pubsub:
            try:
                self.pubsub.punsubscribe()
            except Exception:
                pass
        self.executor.shutdown(wait=False)
        logger.info("Notifier process stopped.")

if __name__ == "__main__":
    notifier = Notifier()
    
    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received. Stopping notifier...")
        notifier.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    notifier.start()
