"""user_hashed_password

Revision ID: 0010_user_hashed_password
Revises: 0009_user_keyword_rotation
Create Date: 2026-08-03 17:04:40.382758

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010_user_hashed_password'
down_revision: Union[str, None] = '0009_user_keyword_rotation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'hashed_password')
