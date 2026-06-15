"""Create streaming_subscription table and seed sample rows

Revision ID: 002
Revises: 001
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "streaming_subscription",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customer.customer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_name", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_index(
        "ix_streaming_subscription_customer_id",
        "streaming_subscription",
        ["customer_id"],
    )

    # Seed sample subscriptions using the first few real customers from Pagila
    op.execute(
        """
        INSERT INTO streaming_subscription (customer_id, plan_name, status, start_date, end_date, auto_renew)
        SELECT customer_id,
               CASE WHEN customer_id % 3 = 0 THEN 'Premium'
                    WHEN customer_id % 3 = 1 THEN 'Standard'
                    ELSE 'Basic' END,
               CASE WHEN customer_id % 5 = 0 THEN 'cancelled' ELSE 'active' END,
               NOW() - INTERVAL '90 days',
               NOW() + INTERVAL '275 days',
               true
        FROM customer
        ORDER BY customer_id
        LIMIT 10
        """
    )


def downgrade() -> None:
    op.drop_index("ix_streaming_subscription_customer_id", table_name="streaming_subscription")
    op.drop_table("streaming_subscription")
