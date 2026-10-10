"""Add durable payment and inventory ledgers.

Revision ID: 8c1d2e3f4a5b
Revises: f7b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "8c1d2e3f4a5b"
down_revision = "f7b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("donation_id", sa.Integer(), sa.ForeignKey("donations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="paystack"),
        sa.Column("provider_reference", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
        sa.Column("event_id", sa.String(length=160), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider_reference", name="uq_payment_transactions_provider_reference"),
        sa.UniqueConstraint("event_id", name="uq_payment_transactions_event_id"),
    )
    for name, col in [
        ("ix_payment_transactions_order_id", "order_id"),
        ("ix_payment_transactions_donation_id", "donation_id"),
        ("ix_payment_transactions_provider_reference", "provider_reference"),
        ("ix_payment_transactions_created_at", "created_at"),
    ]:
        op.create_index(name, "payment_transactions", [col])

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name, col in [
        ("ix_inventory_transactions_product_id", "product_id"),
        ("ix_inventory_transactions_order_id", "order_id"),
        ("ix_inventory_transactions_actor_user_id", "actor_user_id"),
        ("ix_inventory_transactions_transaction_type", "transaction_type"),
        ("ix_inventory_transactions_created_at", "created_at"),
    ]:
        op.create_index(name, "inventory_transactions", [col])

    # Composite indexes used by high-volume admin and application queries.
    op.create_index("ix_applications_program_status_submitted", "applications", ["program_id", "status", "submitted_at"])
    op.create_index("ix_orders_status_payment_created", "orders", ["status", "payment_status", "created_at"])
    op.create_index("ix_posts_published_at", "posts", ["published_at"])
    op.create_index("ix_resources_category_created", "resources", ["category", "created_at"])
    op.create_index("ix_videos_published_featured_created", "video_testimonials", ["is_published", "featured", "created_at"])


def downgrade():
    for name, table in [
        ("ix_videos_published_featured_created", "video_testimonials"),
        ("ix_resources_category_created", "resources"),
        ("ix_posts_published_at", "posts"),
        ("ix_orders_status_payment_created", "orders"),
        ("ix_applications_program_status_submitted", "applications"),
    ]:
        op.drop_index(name, table_name=table)
    for name in [
        "ix_inventory_transactions_created_at", "ix_inventory_transactions_transaction_type",
        "ix_inventory_transactions_actor_user_id", "ix_inventory_transactions_order_id",
        "ix_inventory_transactions_product_id",
    ]:
        op.drop_index(name, table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    for name in [
        "ix_payment_transactions_created_at", "ix_payment_transactions_provider_reference",
        "ix_payment_transactions_donation_id", "ix_payment_transactions_order_id",
    ]:
        op.drop_index(name, table_name="payment_transactions")
    op.drop_table("payment_transactions")
