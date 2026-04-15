"""add indexes on frequently queried columns

Revision ID: 108aac5da60d
Revises: a1b2c3d4e5f6
Create Date: 2026-04-14 19:38:03.099735

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '108aac5da60d'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('application_todos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_application_todos_job_id'), ['job_id'], unique=False)

    with op.batch_alter_table('job_documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_job_documents_job_id'), ['job_id'], unique=False)

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_jobs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_status'), ['status'], unique=False)

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_messages_conversation_id'), ['conversation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_messages_created_at'), ['created_at'], unique=False)

    with op.batch_alter_table('search_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_search_results_conversation_id'), ['conversation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_search_results_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('search_results', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_search_results_created_at'))
        batch_op.drop_index(batch_op.f('ix_search_results_conversation_id'))

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_created_at'))
        batch_op.drop_index(batch_op.f('ix_messages_conversation_id'))

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_status'))
        batch_op.drop_index(batch_op.f('ix_jobs_created_at'))

    with op.batch_alter_table('job_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_job_documents_job_id'))

    with op.batch_alter_table('application_todos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_application_todos_job_id'))
