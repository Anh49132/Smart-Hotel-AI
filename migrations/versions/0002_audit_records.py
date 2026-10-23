"""Record booking transitions, payments and AI review results.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL's bookingstatus type was created by 0001; do not recreate it.
    booking_status = sa.Enum("confirmed", "checked_in", "checked_out", "cancelled", name="bookingstatus").with_variant(
        ENUM("confirmed", "checked_in", "checked_out", "cancelled", name="bookingstatus", create_type=False), "postgresql"
    )
    op.create_table(
        "booking_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("from_status", booking_status, nullable=True),
        sa.Column("to_status", booking_status, nullable=False),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_booking_status_history_booking_id", "booking_status_history", ["booking_id"])
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payments_positive_amount"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_table(
        "ai_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("generated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_results_kind", "ai_results", ["kind"])
    op.create_index("ix_ai_results_review_status", "ai_results", ["review_status"])


def downgrade():
    op.drop_index("ix_ai_results_review_status", table_name="ai_results")
    op.drop_index("ix_ai_results_kind", table_name="ai_results")
    op.drop_table("ai_results")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_booking_status_history_booking_id", table_name="booking_status_history")
    op.drop_table("booking_status_history")
