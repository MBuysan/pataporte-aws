"""Avisos durables, publicados después del commit de negocio."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003_transactional_outbox"
down_revision = "0002_seed_vaccines"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "outbox_events",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("event_type", sa.VARCHAR(50), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.VARCHAR(80), nullable=True),
    )
    op.create_index("ix_outbox_pending", "outbox_events", ["available_at"],
                    postgresql_where=sa.text("dispatched_at IS NULL"))


def downgrade():
    op.drop_index("ix_outbox_pending", table_name="outbox_events")
    op.drop_table("outbox_events")
