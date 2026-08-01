"""job last seen at

Revision ID: 0005_job_last_seen_at
Revises: 82776d9dcbdf
Create Date: 2026-07-29 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_job_last_seen_at'
down_revision: Union[str, None] = '82776d9dcbdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable Column `last_seen_at` to table `jobs`
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(), nullable=True))

    # 2. Backfill existing jobs: last_seen_at = created_at
    op.execute("UPDATE jobs SET last_seen_at = created_at WHERE last_seen_at IS NULL")


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('last_seen_at')
