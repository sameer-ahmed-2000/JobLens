"""users resumes matches

Revision ID: 0004_users_resumes_matches
Revises: 0003_phase6_career_workspace
Create Date: 2026-07-17 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '0004_users_resumes_matches'
down_revision: Union[str, None] = '0003_phase6_career_workspace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection bind
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Enable pgvector if on PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Programmatic Data Extraction (Extract old resumes/projects/skills)
    migrated_resumes = []
    try:
        resumes_raw = bind.execute(sa.text("SELECT id, user_id, experience_years, target_roles, version FROM resumes")).fetchall()
        projects_raw = bind.execute(sa.text("SELECT resume_id, name, description, tech_stack, metrics FROM projects")).fetchall()
        skills_raw = bind.execute(sa.text("SELECT resume_id, name, years_experience, level FROM skills")).fetchall()
        embedding_cache_raw = bind.execute(sa.text("SELECT entity_id, embedding FROM embedding_cache WHERE entity_type = 'resume'")).fetchall()

        # Build embedding dictionary by entity_id
        embeddings_dict = {}
        for row in embedding_cache_raw:
            entity_id = row[0]
            emb_val = row[1]
            if isinstance(emb_val, str):
                try:
                    embeddings_dict[entity_id] = json.loads(emb_val)
                except Exception:
                    pass
            elif isinstance(emb_val, list):
                embeddings_dict[entity_id] = emb_val

        # Map resumes
        for res in resumes_raw:
            res_id, user_id, exp_years, target_roles, version = res
            
            # Fetch skills
            s_names = [s[1] for s in skills_raw if s[0] == res_id]
            
            # Fetch projects
            p_list = []
            for p in projects_raw:
                if p[0] == res_id:
                    techs = p[3]
                    if isinstance(techs, str):
                        try:
                            techs = json.loads(techs)
                        except Exception:
                            techs = []
                    p_list.append({
                        "name": p[1],
                        "description": p[2],
                        "technologies": techs,
                        "metrics": p[4]
                    })
            
            # Build raw_text
            roles = target_roles
            if isinstance(roles, str):
                try:
                    roles = json.loads(roles)
                except Exception:
                    roles = []
            title = roles[0] if roles else "AI Engineer"
            
            raw_text = f"Title: {title}\nExperience: {exp_years or 0.0} years\nSkills: {', '.join(s_names)}"
            for p in p_list:
                raw_text += f"\nProject {p['name']}: {p['description']}"
                if p['technologies']:
                    raw_text += f" (Tech: {', '.join(p['technologies'])})"
            
            # Retrieve cached embedding or default to 384 zeros
            embedding = embeddings_dict.get(res_id, [0.0] * 384)
            
            migrated_resumes.append({
                "id": res_id,
                "user_id": user_id,
                "raw_text": raw_text,
                "parsed_skills": s_names,
                "embedding": embedding,
                "is_active": True,
                "created_at": datetime.utcnow()
            })
    except Exception as e:
        print(f"Skipping migration data extraction (tables might be empty or missing): {e}")

    # 2. Drop Foreign Keys & Tables
    # Safely drop constraints on applications
    if is_postgres:
        try:
            op.drop_constraint('fk_applications_resume_id', 'applications', type_='foreignkey')
        except Exception:
            pass
    else:
        # SQLite constraint drop via batch
        with op.batch_alter_table('applications') as batch_op:
            try:
                batch_op.drop_constraint('fk_applications_resume_id', type_='foreignkey')
            except Exception:
                pass

    op.drop_table('projects')
    op.drop_table('skills')
    op.drop_table('resumes')

    # 3. Create the New Resumes Table
    # Determine embedding column type based on DB engine
    if is_postgres:
        embedding_col_type = sa.UserDefinedType()
        # Custom compilable VECTOR type will be handled by class compiled name, but inside migrations,
        # using the raw postgres type works best:
        from sqlalchemy.dialects.postgresql import ARRAY
        # To support pgvector in Alembic, use raw sql or op.execute for Postgres, ARRAY or custom for sqlalchemy
    
    # We will declare it as sa.JSON or custom type in migrations. To ensure Alembic generates clean SQL
    # on PostgreSQL, we can use sa.Text/sa.JSON for SQLite and sa.NullType or vector for PostgreSQL.
    # Actually, declaring it as sa.JSON (or using raw DDL to alter/create table) is extremely portable, 
    # but since pgvector is required, let's define the resumes table with a VARCHAR/JSON column and then 
    # cast it to vector on postgresql, or use a custom type:
    
    op.create_table(
        'resumes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('parsed_skills', sa.JSON(), nullable=False),
        sa.Column('embedding', sa.JSON() if not is_postgres else sa.NullType(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    if is_postgres:
        # Cast embedding column to vector(384) on Postgres
        op.execute("ALTER TABLE resumes ALTER COLUMN embedding TYPE vector(384) USING embedding::text::vector(384);")

    op.create_index(op.f('ix_resumes_user_id'), 'resumes', ['user_id'], unique=False)

    # Recreate applications foreign key to resumes table
    with op.batch_alter_table('applications') as batch_op:
        batch_op.create_foreign_key(
            'fk_applications_resume_id',
            'resumes',
            ['resume_id'], ['id'],
            ondelete='SET NULL'
        )

    # 4. Insert Migrated Data
    for res in migrated_resumes:
        # For Postgres we need to format vector embedding as string representation or list
        emb_val = res['embedding']
        if is_postgres:
            # Postgres pgvector accepts string representation '[0.1, 0.2, ...]'
            emb_val = str(emb_val)
        else:
            # SQLite accepts JSON list serialized to string
            emb_val = json.dumps(emb_val)
            
        bind.execute(
            sa.text(
                "INSERT INTO resumes (id, user_id, raw_text, parsed_skills, embedding, is_active, created_at) "
                "VALUES (:id, :user_id, :raw_text, :parsed_skills, :embedding, :is_active, :created_at)"
            ),
            {
                "id": res["id"],
                "user_id": res["user_id"],
                "raw_text": res["raw_text"],
                "parsed_skills": json.dumps(res["parsed_skills"]),
                "embedding": emb_val,
                "is_active": res["is_active"],
                "created_at": res["created_at"]
            }
        )

    # 5. Enforce One Active Resume per User Constraint
    # PostgreSQL & SQLite partial index
    op.create_index(
        'uq_active_resume_per_user',
        'resumes',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
        sqlite_where=sa.text('is_active = 1')
    )

    # 6. Alter Users Table
    op.add_column('users', sa.Column('whatsapp_number', sa.String(), nullable=True))
    op.add_column('users', sa.Column('notify_threshold', sa.Float(), nullable=False, server_default='0.85'))
    op.add_column('users', sa.Column('display_threshold', sa.Float(), nullable=False, server_default='0.70'))
    op.add_column('users', sa.Column('token_hash', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_token_hash'), 'users', ['token_hash'], unique=True)

    # 7. Create Job Matches Table
    op.create_table(
        'job_matches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'job_id', name='uq_user_job_match')
    )
    # Composite B-tree index optimized for dashboard query ordering: (user_id, score DESC, created_at DESC)
    op.create_index(
        'ix_job_matches_user_score_created',
        'job_matches',
        ['user_id', 'score', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop job_matches table
    op.drop_table('job_matches')

    # Alter users table: drop columns and index
    op.drop_index(op.f('ix_users_token_hash'), table_name='users')
    op.drop_column('users', 'token_hash')
    op.drop_column('users', 'display_threshold')
    op.drop_column('users', 'notify_threshold')
    op.drop_column('users', 'whatsapp_number')

    # Drop active resume partial index
    op.drop_index('uq_active_resume_per_user', table_name='resumes')

    # Recreate projects and skills tables, and restore old resumes structure
    # Downgrade is best effort to prevent breakage, but schema rebuild is fine
    with op.batch_alter_table('applications') as batch_op:
        try:
            batch_op.drop_constraint('fk_applications_resume_id', type_='foreignkey')
        except Exception:
            pass

    op.drop_table('resumes')

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

    with op.batch_alter_table('applications') as batch_op:
        batch_op.create_foreign_key(
            'fk_applications_resume_id',
            'resumes',
            ['resume_id'], ['id'],
            ondelete='SET NULL'
        )

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
