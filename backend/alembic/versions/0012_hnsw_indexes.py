"""hnsw_indexes

Revision ID: 0012_hnsw_indexes
Revises: 0011_manual_skills_roles
Create Date: 2026-08-05 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012_hnsw_indexes'
down_revision: Union[str, None] = '0011_manual_skills_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_resumes_embedding_hnsw ON resumes USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_resumes_embedding_hnsw")
        op.execute("DROP INDEX IF EXISTS idx_jobs_embedding_hnsw")
