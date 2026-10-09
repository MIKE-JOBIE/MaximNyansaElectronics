"""add indexes for orders and applications

Revision ID: c91d4e7a2b10
Revises: ec9ba258e361
"""
from alembic import op

revision = "c91d4e7a2b10"
down_revision = "ec9ba258e361"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_program_id", "applications", ["program_id"])
    op.create_index("ix_applications_status", "applications", ["status"])


def downgrade():
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_program_id", table_name="applications")
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
