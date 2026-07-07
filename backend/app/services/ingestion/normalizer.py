import logging
from typing import Dict, Any, Optional
from app.models.schemas import RawPosting
from app.nodes.normalize import strip_html

logger = logging.getLogger(__name__)

def normalize_job(raw_item: Dict[str, Any], source_type: str, board: str) -> Optional[RawPosting]:
    """Normalize raw job item from connector into standardized RawPosting Pydantic model."""
    try:
        if source_type.lower() == "greenhouse":
            job_id = f"gh-{board}-{raw_item.get('id')}"
            title = raw_item.get("title", "")
            url = raw_item.get("absolute_url") or f"https://boards.greenhouse.io/{board}/jobs/{raw_item.get('id')}"
            content = raw_item.get("content", "")
            description = strip_html(content).strip()
            company = board.capitalize()

        elif source_type.lower() == "lever":
            job_id = f"lev-{board}-{raw_item.get('id')}"
            title = raw_item.get("text", "")
            url = raw_item.get("hostedUrl") or f"https://jobs.lever.co/{board}/{raw_item.get('id')}"
            desc_plain = raw_item.get("descriptionPlain")
            if desc_plain:
                description = desc_plain.strip()
            else:
                description = strip_html(raw_item.get("description", "")).strip()
            company = board.capitalize()

        elif source_type.lower() == "ashby":
            job_id = f"ash-{board}-{raw_item.get('id')}"
            title = raw_item.get("title", "")
            url = raw_item.get("jobUrl") or f"https://jobs.ashbyhq.com/{board}/{raw_item.get('id')}"
            desc_plain = raw_item.get("descriptionPlain")
            if desc_plain:
                description = desc_plain.strip()
            else:
                description = strip_html(raw_item.get("descriptionHtml", "")).strip()
            company = board.capitalize()
        else:
            logger.warning(f"Unknown source_type '{source_type}' during normalization.")
            return None

        if not title or not description:
            return None

        return RawPosting(
            id=str(job_id),
            title=title.strip(),
            company=company,
            description=description,
            url=url,
            source=source_type.capitalize()
        )
    except Exception as e:
        logger.warning(f"Failed to normalize raw item for {source_type} ({board}): {e}")
        return None
