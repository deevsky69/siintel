"""Aktifkan ekstensi PostGIS dan pgcrypto.

Migration baseline (TASK 010). Belum membuat tabel apa pun —
entitas dibuat mulai TASK 011 mengikuti docs/02-data-dictionary.md.

- postgis  : tipe geometry(Point,4326) dan index spasial (docs/06 §1)
- pgcrypto : gen_random_uuid() untuk primary key UUID (docs/02 K-1)

Revision ID: 0001
Revises:
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    # Ekstensi sengaja tidak di-drop: objek lain di database dapat bergantung padanya.
    pass
