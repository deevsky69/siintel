"""Langganan pemberitahuan wilayah oleh warga.

Naskah Taskap 4.7 b ("Pemberitahuan wilayah"): warga yang memilih menerima pemberitahuan
memperoleh imbauan sesuai kelurahannya. Sebelumnya hanya GRUP WhatsApp yang dapat didaftarkan
(`babinkamtibmas.whatsapp_group_chat_id`); tabel ini untuk percakapan pribadi.

Isinya data pribadi yang diminimalkan — kanal, pengenal percakapan, kelurahan — dan barisnya
dihapus saat warga berhenti (lihat models/area_subscription.py).

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "area_subscriptions",
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("chat_id", sa.String(64), nullable=False),
        sa.Column("kelurahan", sa.String(100), nullable=False),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("advisory_sent_month", sa.String(7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("subscription_id", name="pk_area_subscriptions"),
        sa.UniqueConstraint("channel", "chat_id", name="uq_area_subscriptions_chat"),
        sa.CheckConstraint(
            "channel IN ('WHATSAPP', 'TELEGRAM')", name="area_subscription_channel_allowed"
        ),
    )
    op.create_index("ix_area_subscriptions_kelurahan", "area_subscriptions", ["kelurahan"])
    op.execute(
        "CREATE TRIGGER trg_area_subscriptions_set_updated_at BEFORE UPDATE ON area_subscriptions "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_area_subscriptions_set_updated_at ON area_subscriptions")
    op.execute("DROP INDEX IF EXISTS ix_area_subscriptions_kelurahan")
    op.drop_table("area_subscriptions")
