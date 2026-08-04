"""manual_skills_roles

Revision ID: 0011_manual_skills_roles
Revises: 0010_user_hashed_password
Create Date: 2026-08-04 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011_manual_skills_roles'
down_revision: Union[str, None] = '0010_user_hashed_password'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('manual_core_skills', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('manual_target_role', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'manual_target_role')
    op.drop_column('users', 'manual_core_skills')
