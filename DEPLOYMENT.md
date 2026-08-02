# JobLens — Small-Group Production Deployment & Operations Guide

This guide details step-by-step instructions for deploying JobLens in a small-group production environment (e.g. VPS, EC2, or local server stack).

---

## 🏗️ Architecture & Process Map

A fully functional JobLens deployment consists of:

1. **PostgreSQL Database** (with `pgvector` extension enabled for resume & job embeddings)
2. **Redis 7** (Event pub/sub, SSE ticket manager, and background queue)
3. **FastAPI Web Server** (`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`)
4. **Embedding Worker Process** (`python -m app.services.ingestion.embedding_worker`)
5. **Scoring Worker Process** (`python -m app.services.ingestion.scoring_worker`)
6. **Notifier Process** (`python -m app.notifier`)
7. **Scheduler Process** (`python -m app.services.job_scheduler`)
8. **Vite React Frontend** (`npm run dev` or production build served via Nginx/Caddy)
9. **Automated Database Backup** (`python scripts/backup_db.py` on daily cron)

---

## 🔑 Environment Configuration

Create or edit `/path/to/JobLens/backend/.env`:

```env
# FastAPI Core
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production

# Database Configuration (PostgreSQL + pgvector)
DATABASE_URL=postgresql://joblens_user:secure_password@localhost:5432/joblens

# Self-Serve Onboarding Invite Code Protection
# IMPORTANT: Replace this default invite token with your private group secret!
SIGNUP_INVITE_TOKEN=your-private-group-invite-token

# LLM Provider Configuration (per-role; all default to "ollama" if unset)
# Role-to-provider mapping — set each to one of: "ollama" | "freemodel" | "openai" | "groq" | "gemini"
# Leave a role blank to inherit LLM_PROVIDER_DEFAULT.
LLM_PROVIDER_DEFAULT=ollama        # global fallback when a role is unset
LLM_PROVIDER_RATIONALE=groq        # fit rationale: cheap, fast, frequent
LLM_PROVIDER_GAP_ANALYSIS=gemini   # JD/gap extraction: structured JSON, accuracy first
LLM_PROVIDER_RESUME_PARSING=gemini # resume parsing: same extraction shape as gap_analysis
LLM_PROVIDER_NOTIFICATION=groq     # notification teaser: cheap, low-stakes

# FreeModel.dev keys (if LLM_PROVIDER_*=freemodel)
# FREEMODEL_API_KEY=your_freemodel_key
# FREEMODEL_BASE_URL=https://api.freemodel.dev/v1
# FREEMODEL_MODEL=auto

# Groq keys (if LLM_PROVIDER_*=groq) — https://console.groq.com/
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Gemini keys (if LLM_PROVIDER_*=gemini) — https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash

# Legacy note: the old LLM_PROVIDER=<name> is still supported as a fallback for
# LLM_PROVIDER_DEFAULT, so existing .env files keep working without modification.

# Aggregators Configuration
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
ADZUNA_COUNTRY=in
ADZUNA_ENABLED=true

JOOBLE_API_KEY=your_jooble_key
JOOBLE_ENABLED=true

REMOTIVE_ENABLED=true
ARBEITNOW_ENABLED=true
LIVE_SEARCH_MIN_INTERVAL_MINUTES=15

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=notifications@yourdomain.com
SMTP_PASSWORD=app_password_here
SMTP_FROM=noreply@joblens.ai

# WhatsApp API Configuration (Optional)
WHATSAPP_API_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_id

# CORS & Notification Deep-Links
FRONTEND_URL=http://localhost:5173
```

---

## 🚀 Database Setup & Migrations

1. Ensure PostgreSQL has the `pgvector` extension enabled:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Run database migrations using Alembic:
   ```bash
   cd backend
   uv run alembic upgrade head
   ```
3. Seed default job sources and ontology data:
   ```bash
   uv run python -c "from app.services.seeder import seed_if_empty; seed_if_empty()"
   ```

---

## 👥 User Onboarding

### Option A: Self-Serve Invite Signup (Recommended)
Distribute your `SIGNUP_INVITE_TOKEN` to your group members. Each user submits a request to:

`POST /api/auth/signup`
```json
{
  "name": "Alex Smith",
  "email": "alex@example.com",
  "invite_code": "your-private-group-invite-token",
  "title": "Senior AI Architect",
  "years_experience": 6.0,
  "skills": ["Python", "PyTorch", "LangGraph", "FastAPI"],
  "projects": [
    {
      "name": "LLM Agent Platform",
      "description": "Multi-agent framework with RAG",
      "technologies": ["Python", "LangChain"]
    }
  ]
}
```
*Response*:
```json
{
  "user": { "id": "...", "name": "Alex Smith", "email": "alex@example.com" },
  "raw_token": "a1b2c3d4e5f6...",
  "message": "Account created successfully..."
}
```
Save the returned `raw_token`. Pass it in HTTP request headers:
`Authorization: Bearer a1b2c3d4e5f6...`

### Option B: CLI Onboarding (Admin Import)
To onboard a user manually via JSON resume file:
```bash
python import_resume.py /path/to/resume.json user_id_name
```

---

## ⚙️ Background Services & Process Supervision

For production reliability, manage backend background processes using `systemd` or Docker Compose.

### Systemd Service Example (`/etc/systemd/system/joblens-api.service`):
```ini
[Unit]
Description=JobLens FastAPI Web Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/JobLens/backend
ExecStart=/home/ubuntu/.local/bin/uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/JobLens/backend/.env

[Install]
WantedBy=multi-user.target
```

---

## 💾 Automated Database Backups & Restore Drills

### Automated Backup Execution
Run `python scripts/backup_db.py` to create timestamped dumps in `backend/backups/`.

Add to system crontab (`crontab -e`):
```cron
# Run daily database backup at 3:00 AM
0 3 * * * cd /home/ubuntu/JobLens/backend && /home/ubuntu/.local/bin/uv run python scripts/backup_db.py >> /home/ubuntu/JobLens/backend/backups/backup.log 2>&1
```

### Disaster Recovery Restore Drill
To verify database backup restoration against a temporary test database:
```bash
cd backend
python scripts/backup_db.py --restore-drill ./backups/joblens_backup_20260720_230513.sql
```
