"""Grup WhatsApp warga per kelurahan dan jejak pengiriman imbauan bulanan.

Keputusan pemilik proyek 4 November 2026: bot (nomor cadangan WAHA, peragaan) dimasukkan ke
grup warga/RT/RW/Babin per kelurahan; imbauan kehati-hatian bulan berjalan dikirim OTOMATIS
awal bulan, dan atas permintaan lewat /rekomendasi. Grup didaftarkan dari dalam grup dengan
/daftar <kelurahan>; chat id-nya disimpan pada baris Babinkamtibmas kelurahan itu.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "babinkamtibmas",
        sa.Column("whatsapp_group_chat_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "babinkamtibmas",
        sa.Column("advisory_sent_month", sa.String(7), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("babinkamtibmas", "advisory_sent_month")
    op.drop_column("babinkamtibmas", "whatsapp_group_chat_id")
