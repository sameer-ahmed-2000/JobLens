"""add ingestion runs

Revision ID: 0002_add_ingestion_runs
Revises: 0001_initial_schema
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_add_ingestion_runs'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('jobs_fetched', sa.Integer(), nullable=True),
        sa.Column('jobs_inserted', sa.Integer(), nullable=True),
        sa.Column('jobs_updated', sa.Integer(), nullable=True),
        sa.Column('duplicates_removed', sa.Integer(), nullable=True),
        sa.Column('failures', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingestion_runs_source'), 'ingestion_runs', ['source'], unique=False)
    op.create_index(op.f('ix_ingestion_runs_started_at'), 'ingestion_runs', ['started_at'], unique=False)


def downgrade() -> None:
    op.drop_table('ingestion_runs')
