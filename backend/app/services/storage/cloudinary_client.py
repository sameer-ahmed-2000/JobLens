import os
import sys
import uuid
import time
import logging
import cloudinary
import cloudinary.uploader
from cloudinary import utils
from app.config import settings

logger = logging.getLogger(__name__)

# Check if we are running in a test environment (under pytest or with ENVIRONMENT=test)
is_test_env = (
    os.getenv("ENVIRONMENT") == "test"
    or "pytest" in sys.modules
    or "test" in sys.argv[0]
)

# Determine if Cloudinary is fully configured
has_credentials = bool(
    settings.cloudinary_cloud_name
    and settings.cloudinary_api_key
    and settings.cloudinary_api_secret
)

if has_credentials:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )
    _use_mock = False
    logger.info("Cloudinary client initialized successfully.")
else:
    if is_test_env:
        _use_mock = True
        logger.warning("Cloudinary credentials missing in test environment. Falling back to MOCK storage.")
    else:
        _use_mock = False
        # Do not raise error immediately so import works, but fail loudly on operations
        logger.error("CRITICAL: Cloudinary credentials are not configured in development/production.")

class CloudinaryConfigError(RuntimeError):
    pass

def _verify_configuration():
    if not has_credentials and not is_test_env:
        raise CloudinaryConfigError(
            "Cloudinary credentials are not configured. Please set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables."
        )

def upload_resume_file(file_bytes: bytes, filename: str, user_id: str) -> dict:
    """
    Uploads file to Cloudinary as an authenticated raw asset.
    In test environments, falls back to a mock response if credentials are missing.
    """
    _verify_configuration()

    if _use_mock:
        mock_public_id = f"mock_resumes/{user_id}/{uuid.uuid4()}_{filename}"
        return {
            "public_id": mock_public_id,
            "secure_url": f"https://res.cloudinary.com/mock-cloud/raw/authenticated/v1/{mock_public_id}",
            "bytes": len(file_bytes),
            "format": filename.split(".")[-1] if "." in filename else ""
        }

    try:
        # Uploading as an authenticated raw resource so it's private by default
        response = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            type="authenticated",
            folder=f"resumes/{user_id}",
            filename=filename
        )
        return response
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}", exc_info=True)
        raise e

def get_signed_download_url(public_id: str, expires_in_seconds: int = 300) -> str:
    """
    Generates a secure, short-lived signed download URL for an authenticated asset.
    """
    _verify_configuration()

    if _use_mock:
        return f"https://res.cloudinary.com/mock-cloud/raw/authenticated/v1/{public_id}?mock-signed=true&expires={int(time.time() + expires_in_seconds)}"

    try:
        # Generate private download URL for authenticated raw assets
        # Standard signature for private authenticated raw assets
        ext = public_id.split(".")[-1] if "." in public_id else ""
        url = utils.private_download_url(
            public_id,
            format=ext,
            resource_type="raw",
            type="authenticated",
            expires_at=int(time.time() + expires_in_seconds)
        )
        return url
    except Exception as e:
        logger.error(f"Failed to generate signed download URL for {public_id}: {e}", exc_info=True)
        raise e

def delete_resume_file(public_id: str) -> dict:
    """
    Deletes the raw asset from Cloudinary.
    """
    _verify_configuration()

    if _use_mock:
        return {"result": "ok"}

    try:
        response = cloudinary.uploader.destroy(
            public_id,
            resource_type="raw",
            type="authenticated"
        )
        return response
    except Exception as e:
        logger.error(f"Failed to delete Cloudinary asset {public_id}: {e}", exc_info=True)
        raise e
