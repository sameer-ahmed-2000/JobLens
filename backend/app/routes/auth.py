import hashlib
import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.repositories.uow import UnitOfWork
from app.models.schemas import SignupRequest, SignupResponse, UserProfileSchema

logger = logging.getLogger("auth")

security = HTTPBearer()
router = APIRouter(prefix="/auth", tags=["auth"])

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    HTTPBearer dependency resolving the client token to a user ID.
    Hashes the incoming raw token with SHA-256 and queries the database token_hash.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing."
        )

    # Compute SHA-256 hash of the token
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with UnitOfWork() as uow:
        user = uow.users.get_by_token_hash(token_hash)
        if user:
            return user["id"]

    logger.warning(f"Failed authentication attempt with token hash: {token_hash}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token."
    )

@router.post("/signup", response_model=SignupResponse)
def signup(req: SignupRequest):
    """
    Self-serve user signup with invite token protection.
    1. Compares invite_code against SIGNUP_INVITE_TOKEN using constant-time comparison.
    2. Validates email uniqueness.
    3. Generates secure raw_token + SHA-256 token_hash.
    4. Creates UserORM record & ResumeORM record with synchronous vector embedding.
    5. Returns raw_token ONCE to the user.
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

        # 3. Token generation
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # 4. User creation
        user_dict = uow.users.create(
            name=req.name.strip(),
            email=req.email.strip().lower(),
            whatsapp_number=req.whatsapp_number.strip() if req.whatsapp_number else None,
            token_hash=token_hash
        )

        # 5. Resume creation with synchronous vector embedding
        uow.resumes.upsert_resume(
            user_id=user_dict["id"],
            title=req.title.strip() if req.title else "Software Engineer",
            years_experience=req.years_experience if req.years_experience is not None else 0.0,
            skills=req.skills or [],
            projects=req.projects or []
        )

        uow.commit()

        user_profile = UserProfileSchema(
            id=user_dict["id"],
            name=user_dict["name"],
            email=user_dict["email"],
            whatsapp_number=user_dict["whatsapp_number"],
            notify_threshold=user_dict["notify_threshold"],
            display_threshold=user_dict["display_threshold"]
        )

        return SignupResponse(user=user_profile, raw_token=raw_token)

