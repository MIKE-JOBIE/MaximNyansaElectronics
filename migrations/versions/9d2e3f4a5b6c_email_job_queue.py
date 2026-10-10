"""Add durable email job queue.

Revision ID: 9d2e3f4a5b6c
Revises: 8c1d2e3f4a5b
"""
from alembic import op
import sqlalchemy as sa
revision = "9d2e3f4a5b6c"
down_revision = "8c1d2e3f4a5b"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "email_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("recipients", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_email_jobs_status", "email_jobs", ["status"])
    op.create_index("ix_email_jobs_available_at", "email_jobs", ["available_at"])
    op.create_index("ix_email_jobs_created_at", "email_jobs", ["created_at"])

def downgrade():
    op.drop_index("ix_email_jobs_created_at", table_name="email_jobs")
    op.drop_index("ix_email_jobs_available_at", table_name="email_jobs")
    op.drop_index("ix_email_jobs_status", table_name="email_jobs")
    op.drop_table("email_jobs")
