import logging
from typing import List, Dict, Any
from app.repositories.uow import UnitOfWork
from app.models.orm import JobSourceORM

logger = logging.getLogger(__name__)

class SourceRegistry:
    @staticmethod
    def get_active_sources() -> List[Dict[str, Any]]:
        """Query authoritative JobSourceORM table for active job sources."""
        try:
            with UnitOfWork() as uow:
                sources = uow.session.query(JobSourceORM).filter(JobSourceORM.is_active == True).all()
                result = []
                for s in sources:
                    # Name is expected to be in format "SourceType:BoardName" or just "SourceType"
                    parts = s.name.split(":", 1)
                    source_type = parts[0]
                    board = parts[1] if len(parts) > 1 else s.url
                    result.append({
                        "id": s.id,
                        "name": s.name,
                        "source_type": source_type,
                        "board": board or s.url,
                        "url": s.url
                    })
                return result
        except Exception as e:
            logger.error(f"Failed to load active sources from registry: {e}")
            return []
