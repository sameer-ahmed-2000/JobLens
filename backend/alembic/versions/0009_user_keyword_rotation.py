"""add last_keyword_search_at to users

Revision ID: 0009_user_keyword_rotation
Revises: 0008_resume_extraction_method
Create Date: 2026-08-03 11:30:00.000000

Tracks when each user last had a resume-keyword-scoped aggregator search run on
their behalf by the background scheduler's rotation. NULL means "never searched"
and sorts first so every active user gets covered at least once before anyone
gets a second turn.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009_user_keyword_rotation'
down_revision: Union[str, None] = '0008_resume_extraction_method'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('last_keyword_search_at', sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_keyword_search_at')
