import filetype
from app.config import settings

def validate_resume_file(file_bytes: bytes, filename: str) -> None:
    """
    Validates the uploaded file against allowed size, extensions, and magic-byte signatures.
    Raises ValueError if validation fails.
    """
    # 1. Size check
    max_bytes = settings.resume_max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValueError(f"File size exceeds maximum limit of {settings.resume_max_size_mb} MB")

    # 2. Extension check
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ("pdf", "docx"):
        raise ValueError("Unsupported file extension. Only .pdf and .docx are allowed.")

    # 3. Magic-byte verification
    kind = filetype.guess(file_bytes)
    
    if kind is None:
        # Fallback to manual byte checks if filetype returns None
        # PDF files begin with %PDF (hex: 25 50 44 46)
        # DOCX/ZIP files begin with PK (hex: 50 4B 03 04)
        if ext == "pdf" and not file_bytes.startswith(b"%PDF"):
            raise ValueError("Magic-byte check failed: File content does not match PDF signature.")
        elif ext == "docx" and not file_bytes.startswith(b"PK\x03\x04"):
            raise ValueError("Magic-byte check failed: File content does not match DOCX signature.")
        return

    # Check mime type alignment
    mime = kind.mime.lower()
    if ext == "pdf":
        if "pdf" not in mime:
            raise ValueError(f"Magic-byte check failed: Expected PDF, got file signature matching {kind.mime}")
    elif ext == "docx":
        # docx files are zip archives containing xml
        if "word" not in mime and "zip" not in mime and "application/octet-stream" not in mime:
            raise ValueError(f"Magic-byte check failed: Expected DOCX, got file signature matching {kind.mime}")
