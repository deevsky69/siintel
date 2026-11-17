"""Metode peringkat bulanan: model dipakai, dua pembanding baru.

Penyesuaian ke naskah Taskap Bab IV (keputusan pemilik proyek 17 November 2026):

- MODEL kini benar-benar dihitung (gradient boosting, services/monthly_model.py);
- pembanding bertambah: HISTORY_1M (bulan sebelumnya) dan ANNUAL (peta tahunan tetap),
  melengkapi HISTORY_3M dan HISTORY_12M — keempatnya ada pada Tabel 12 naskah.

Hanya CHECK `method` pada `monthly_rankings` yang berubah. Tidak ada baris yang diubah.

Downgrade menghapus peringkat beku bermetode baru yang TIDAK dirujuk produk bulanan; bila
ada produk yang merujuknya, downgrade berhenti dengan galat FK — produk yang sudah
ditetapkan pimpinan tidak boleh ikut hilang diam-diam.

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "monthly_rankings"
CONSTRAINT = "monthly_ranking_method_allowed"
OLD = "method IN ('HISTORY_3M', 'HISTORY_12M', 'MODEL')"
NEW = "method IN ('HISTORY_3M', 'HISTORY_12M', 'MODEL', 'HISTORY_1M', 'ANNUAL')"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, NEW)


def downgrade() -> None:
    op.execute(f"DELETE FROM {TABLE} WHERE method IN ('HISTORY_1M', 'ANNUAL')")  # noqa: S608
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, OLD)
