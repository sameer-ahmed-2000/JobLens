import hashlib
import logging
import secrets
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.repositories.uow import UnitOfWork
from app.models.schemas import SignupRequest, SignupResponse, SigninRequest, UserProfileSchema
from app.rate_limiter import limiter

logger = logging.getLogger("auth")

security = HTTPBearer()
router = APIRouter(prefix="/auth", tags=["auth"])

def _embed_resume_background(user_id: str, title: str, years_experience: float, skills: list, projects: list):
    """Runs after the response is sent — embedding latency no longer blocks signup."""
    try:
        with UnitOfWork() as uow:
            uow.resumes.upsert_resume(
                user_id=user_id,
                title=title,
                years_experience=years_experience,
                skills=skills,
                projects=projects
            )
            uow.commit()
    except Exception:
        logger.exception(f"Background resume embedding failed for user_id={user_id}")

# Cost 12 is typical, but we reduce to 10 for faster sign-ins
DUMMY_HASH = bcrypt.hashpw(b"dummy_password", bcrypt.gensalt(rounds=10)).decode("utf-8")

def get_password_hash(password: str) -> str:
    # Validate length again just in case, though schema covers it
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError("Password is too long (exceeds 72 bytes)")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=10)).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode('utf-8')
        if len(pw_bytes) > 72:
            return False
        return bcrypt.checkpw(pw_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_jwt_token(user_id: str, email: str) -> str:
    """
    Generates a signed JWT token for the given user.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expiration_minutes)

    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    HTTPBearer dependency resolving the client token to a user ID.
    First attempts stateless verification via JWT decoding.
    Expired JWTs are rejected immediately. Legacy non-JWT tokens fall back to DB lookup.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing."
        )

    # 1. Attempt JWT validation
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id:
            with UnitOfWork() as uow:
                user = uow.users.get_by_id(user_id)
                if user:
                    return user_id
    except jwt.ExpiredSignatureError:
        logger.info("Authentication attempt with expired JWT token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired."
        )
    except jwt.PyJWTError as e:
        logger.debug(f"JWT verification failed, falling back to legacy token validation: {e}")

    # 2. Legacy Fallback: Hash raw token and lookup in database
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with UnitOfWork() as uow:
        user = uow.users.get_by_token_hash(token_hash)
        if user:
            return user["id"]

    masked_hash = f"{token_hash[:8]}..." if token_hash else "None"
    logger.warning(f"Failed authentication attempt with token/hash prefix: {masked_hash}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token."
    )



@router.post("/signup", response_model=SignupResponse)
@limiter.limit("5/minute")
def signup(request: Request, req: SignupRequest, background_tasks: BackgroundTasks):
    """
    Self-serve user signup with invite token protection.
    1. Compares invite_code against SIGNUP_INVITE_TOKEN using constant-time comparison.
    2. Validates email uniqueness.
    3. Hashes password using bcrypt.
    4. Generates secure raw_token + SHA-256 token_hash for legacy support.
    5. Creates UserORM record & ResumeORM record with synchronous vector embedding.
    6. Returns raw_token ONCE to the user.
    """
    # 1. Invite code verification
    if not req.invite_code or not secrets.compare_digest(req.invite_code.strip(), settings.signup_invite_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing invite code."
        )

    # 2. Check existing user by email
    with UnitOfWork() as uow:
        existing = uow.users.get_by_email(req.email.strip().lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        # 3. Hash password
        hashed_password = get_password_hash(req.password)

        # 4. Token generation
        user_id = str(uuid.uuid4())
        raw_token = create_jwt_token(user_id, req.email.strip().lower())
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # 5. User creation
        user_dict = uow.users.create(
            user_id=user_id,
            name=req.name.strip(),
            email=req.email.strip().lower(),
            whatsapp_number=req.whatsapp_number.strip() if req.whatsapp_number else None,
            token_hash=token_hash,
            hashed_password=hashed_password
        )

        uow.commit()

    # 6. Defer the slow embedding work until after the response is returned
    background_tasks.add_task(
        _embed_resume_background,
        user_id=user_dict["id"],
        title=req.title.strip() if req.title else "Software Engineer",
        years_experience=req.years_experience if req.years_experience is not None else 0.0,
        skills=req.skills or [],
        projects=req.projects or []
    )

    user_profile = UserProfileSchema(
        id=user_dict["id"],
        name=user_dict["name"],
        email=user_dict["email"],
        whatsapp_number=user_dict["whatsapp_number"],
        notify_threshold=user_dict["notify_threshold"],
        display_threshold=user_dict["display_threshold"]
    )

    return SignupResponse(user=user_profile, raw_token=raw_token)


@router.post("/signin", response_model=SignupResponse)
@limiter.limit("5/minute")
def signin(request: Request, req: SigninRequest):
    """
    Standard email and password authentication.
    Returns a fresh JWT token on success.
    """
    with UnitOfWork() as uow:
        user = uow.users.get_by_email(req.email.strip().lower())

        # Timing attack mitigation: always run bcrypt verification
        if not user or not user.get("hashed_password"):
            verify_password(req.password, DUMMY_HASH)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password."
            )

        if not verify_password(req.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password."
            )

        # Success - generate new JWT
        raw_token = create_jwt_token(user["id"], user["email"])
        
        user_profile = UserProfileSchema(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            whatsapp_number=user["whatsapp_number"],
            notify_threshold=user["notify_threshold"],
            display_threshold=user["display_threshold"]
        )

        return SignupResponse(user=user_profile, raw_token=raw_token)
