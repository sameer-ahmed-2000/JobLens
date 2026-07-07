"""phase6 career workspace schema additions

Revision ID: 0003_phase6_career_workspace
Revises: 0002_add_ingestion_runs
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003_phase6_career_workspace'
down_revision: Union[str, None] = '0002_add_ingestion_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add resume_id to applications (nullable — backward compatible)
    op.add_column('applications', sa.Column('resume_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_applications_resume_id'), 'applications', ['resume_id'], unique=False)
    op.create_foreign_key(
        'fk_applications_resume_id',
        'applications', 'resumes',
        ['resume_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add created_at to applications (backfill with current time for existing rows)
    op.add_column('applications', sa.Column('created_at', sa.DateTime(), nullable=True))

    # Add updated_at to interview_notes
    op.add_column('interview_notes', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_notes', 'updated_at')
    op.drop_column('applications', 'created_at')
    op.drop_constraint('fk_applications_resume_id', 'applications', type_='foreignkey')
    op.drop_index(op.f('ix_applications_resume_id'), table_name='applications')
    op.drop_column('applications', 'resume_id')
