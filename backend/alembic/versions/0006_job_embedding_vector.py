"""convert jobs.embedding from JSON to pgvector VECTOR(384)

Revision ID: 0006_job_embedding_vector
Revises: 0005_job_last_seen_at
Create Date: 2026-08-02
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_job_embedding_vector'
down_revision: Union[str, None] = '0005_job_last_seen_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("ALTER TABLE jobs ADD COLUMN embedding_v2 vector(384)")
    op.execute("""
        UPDATE jobs
        SET embedding_v2 = embedding::text::vector
        WHERE embedding IS NOT NULL
    """)
    op.execute("ALTER TABLE jobs DROP COLUMN embedding")
    op.execute("ALTER TABLE jobs RENAME COLUMN embedding_v2 TO embedding")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE jobs ADD COLUMN embedding_json JSON")
    op.execute("UPDATE jobs SET embedding_json = to_jsonb(embedding) WHERE embedding IS NOT NULL")
    op.execute("ALTER TABLE jobs DROP COLUMN embedding")
    op.execute("ALTER TABLE jobs RENAME COLUMN embedding_json TO embedding")
