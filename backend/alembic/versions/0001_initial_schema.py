"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-07-05 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'resumes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('experience_years', sa.Float(), nullable=True),
        sa.Column('target_roles', sa.JSON(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resumes_user_id'), 'resumes', ['user_id'], unique=False)

    op.create_table(
        'embedding_cache',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('section', sa.String(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_embedding_cache_entity_type'), 'embedding_cache', ['entity_type'], unique=False)
    op.create_index(op.f('ix_embedding_cache_entity_id'), 'embedding_cache', ['entity_id'], unique=False)

    op.create_table(
        'projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('resume_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tech_stack', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_resume_id'), 'projects', ['resume_id'], unique=False)

    op.create_table(
        'skills',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('resume_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('years_experience', sa.Float(), nullable=True),
        sa.Column('level', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_resume_id'), 'skills', ['resume_id'], unique=False)
    op.create_index(op.f('ix_skills_name'), 'skills', ['name'], unique=False)

    op.create_table(
        'companies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('career_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=False)
    op.create_index(op.f('ix_companies_career_url'), 'companies', ['career_url'], unique=False)

    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('employment_type', sa.String(), nullable=True),
        sa.Column('salary', sa.String(), nullable=True),
        sa.Column('salary_currency', sa.String(), nullable=True),
        sa.Column('remote', sa.Boolean(), nullable=True),
        sa.Column('seniority', sa.String(), nullable=True),
        sa.Column('experience_required', sa.Float(), nullable=True),
        sa.Column('posted_date', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_company_id'), 'jobs', ['company_id'], unique=False)
    op.create_index(op.f('ix_jobs_title'), 'jobs', ['title'], unique=False)
    op.create_index(op.f('ix_jobs_url'), 'jobs', ['url'], unique=True)

    op.create_table(
        'applications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_job_id'), 'applications', ['job_id'], unique=False)
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)

    op.create_table(
        'gap_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('resume_version', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('overall_summary', sa.Text(), nullable=False),
        sa.Column('report_data', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gap_reports_job_id'), 'gap_reports', ['job_id'], unique=False)
    op.create_index(op.f('ix_gap_reports_user_id'), 'gap_reports', ['user_id'], unique=False)

    op.create_table(
        'job_sources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_fetched_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_sources_name'), 'job_sources', ['name'], unique=False)

    op.create_table(
        'interview_notes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_notes_application_id'), 'interview_notes', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_table('interview_notes')
    op.drop_table('job_sources')
    op.drop_table('gap_reports')
    op.drop_table('applications')
    op.drop_table('jobs')
    op.drop_table('companies')
    op.drop_table('skills')
    op.drop_table('projects')
    op.drop_table('embedding_cache')
    op.drop_table('resumes')
    op.drop_table('users')
