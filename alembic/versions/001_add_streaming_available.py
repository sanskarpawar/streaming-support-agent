"""Add streaming_available column to film table

Revision ID: 001
Revises:
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "film",
        sa.Column(
            "streaming_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Seed a handful of films as streaming-available for demo purposes
    op.execute(
        """
        UPDATE film
        SET streaming_available = true
        WHERE film_id IN (
            SELECT film_id FROM film ORDER BY film_id LIMIT 50
        )
        """
    )


def downgrade() -> None:
    op.drop_column("film", "streaming_available")
