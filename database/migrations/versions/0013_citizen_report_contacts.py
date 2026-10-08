"""Kanal perpesanan (Telegram / WhatsApp) — `citizen_report_contacts`.

Keputusan pemilik proyek 8 Oktober 2026: laporan masyarakat dapat masuk lewat bot Telegram
(dan WhatsApp setelah akun bisnis Meta tersedia), dan identitas percakapan BOLEH disimpan
untuk mengabari perkembangan laporan. Tabelnya terpisah dari `citizen_reports` supaya
laporan web/aplikasi tetap tanpa identitas, dan supaya kontak dapat dihapus tanpa menyentuh
laporannya. Batas-batasnya ditulis di `models/citizen_report_contact.py`.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "citizen_report_contacts",
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column(
            "chat_id",
            sa.String(64),
            nullable=False,
            comment="Pengenal percakapan: chat id Telegram, nomor WhatsApp. Data pribadi.",
        ),
        sa.Column("last_notified_status", sa.String(50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("contact_id", name="pk_citizen_report_contacts"),
        sa.UniqueConstraint("report_id", name="uq_citizen_report_contacts_report_id"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["citizen_reports.report_id"],
            name="fk_citizen_report_contacts_report_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("channel IN ('TELEGRAM', 'WHATSAPP')", name="contact_channel_known"),
    )
    op.create_index(
        "ix_citizen_report_contacts_chat", "citizen_report_contacts", ["channel", "chat_id"]
    )
    op.execute(
        "CREATE TRIGGER trg_citizen_report_contacts_set_updated_at BEFORE UPDATE ON "
        "citizen_report_contacts FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_citizen_report_contacts_set_updated_at ON citizen_report_contacts")
    op.execute("DROP INDEX IF EXISTS ix_citizen_report_contacts_chat")
    op.drop_table("citizen_report_contacts")
