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
    with op.batch_alter_table('applications') as batch_op:
        batch_op.add_column(sa.Column('resume_id', sa.String(), nullable=True))
        batch_op.create_index(op.f('ix_applications_resume_id'), ['resume_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_applications_resume_id',
            'resumes',
            ['resume_id'], ['id'],
            ondelete='SET NULL'
        )
        # Add created_at to applications (backfill with current time for existing rows)
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # Add updated_at to interview_notes
    with op.batch_alter_table('interview_notes') as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('interview_notes') as batch_op:
        batch_op.drop_column('updated_at')
    with op.batch_alter_table('applications') as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_constraint('fk_applications_resume_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_applications_resume_id'))
        batch_op.drop_column('resume_id')
