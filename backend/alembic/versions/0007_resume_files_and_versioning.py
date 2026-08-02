"""resume files and versioning

Revision ID: 0007_resume_files_and_versioning
Revises: 0006_job_embedding_vector
Create Date: 2026-08-02 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_resume_files_and_versioning'
down_revision: Union[str, None] = '0006_job_embedding_vector'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create resume_files table
    op.create_table(
        'resume_files',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('resume_id', sa.String(), nullable=True),
        sa.Column('storage_provider', sa.String(), nullable=False, server_default='cloudinary'),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=False),
        sa.Column('processing_status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('processing_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_resume_files_user_id', 'resume_files', ['user_id'])
    op.create_index('ix_resume_files_sha256', 'resume_files', ['sha256'])

    # 2. Add columns to resumes table with batch_alter_table for SQLite compatibility
    with op.batch_alter_table('resumes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('parser_version', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('resume_file_id', sa.String(), nullable=True))
        batch_op.create_foreign_key('fk_resumes_resume_file_id', 'resume_files', ['resume_file_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('resumes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_resumes_resume_file_id', type_='foreignkey')
        batch_op.drop_column('resume_file_id')
        batch_op.drop_column('parser_version')
        batch_op.drop_column('version')

    op.drop_index('ix_resume_files_sha256', table_name='resume_files')
    op.drop_index('ix_resume_files_user_id', table_name='resume_files')
    op.drop_table('resume_files')
