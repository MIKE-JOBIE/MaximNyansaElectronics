"""Production integrity hardening: audit log, application uniqueness, remove stray video payment fields.

Revision ID: f7b2c3d4e5f6
Revises: c91d4e7a2b10
"""
from alembic import op
import sqlalchemy as sa

revision = "f7b2c3d4e5f6"
down_revision = "c91d4e7a2b10"
branch_labels = None
depends_on = None


def upgrade():
    # The old batch-4 migration accidentally added these fields to video_testimonials.
    # They are not used by the application and belong on orders/donations instead.
    with op.batch_alter_table("video_testimonials", schema=None) as batch_op:
        batch_op.drop_index("ix_video_testimonials_payment_ref")
        batch_op.drop_column("payment_status")
        batch_op.drop_column("payment_ref")

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name, col in [
        ("ix_audit_logs_user_id", "user_id"),
        ("ix_audit_logs_action", "action"),
        ("ix_audit_logs_entity", "entity"),
        ("ix_audit_logs_entity_id", "entity_id"),
        ("ix_audit_logs_created_at", "created_at"),
    ]:
        op.create_index(name, "audit_logs", [col])

    # Prevent two concurrent active applications by the same user for the same program.
    # This preserves re-application after rejection while making the active states unique.
    active = sa.text("status IN ('pending','approved','enrolled')")
    op.create_index(
        "uq_applications_active_user_program",
        "applications",
        ["user_id", "program_id"],
        unique=True,
        postgresql_where=active,
        sqlite_where=active,
    )


def downgrade():
    op.drop_index("uq_applications_active_user_program", table_name="applications")
    for name in [
        "ix_audit_logs_created_at", "ix_audit_logs_entity_id", "ix_audit_logs_entity",
        "ix_audit_logs_action", "ix_audit_logs_user_id",
    ]:
        op.drop_index(name, table_name="audit_logs")
    op.drop_table("audit_logs")
    # Do not restore the stray video payment columns: the prior migration was defective.
