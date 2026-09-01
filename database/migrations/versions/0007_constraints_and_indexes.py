"""Peninjauan constraint & index.

TASK 016. Sebagian besar constraint dan index sudah dipasang bersama tabelnya, sehingga
task ini adalah **peninjauan berbasis bukti** terhadap database nyata, bukan penambahan
index secara membabi buta (docs/08 TASK 016).

Tiga celah yang ditemukan lewat pemeriksaan `pg_constraint`/`pg_index` dan uji langsung:

1. **10 kolom foreign key tanpa index.** PostgreSQL tidak membuat index otomatis untuk
   kolom FK. Setiap `DELETE`/`UPDATE` pada tabel induk memicu sequential scan pada tabel
   anak untuk memeriksa `RESTRICT`/`CASCADE`, dan jalur join ikut lambat.
   Aturan yang dipakai: **setiap kolom FK memiliki index**, kecuali sudah menjadi kolom
   pertama index lain.

2. **`updated_at` tidak pernah berubah pada UPDATE lewat SQL langsung.** `onupdate` pada
   SQLAlchemy hanya berlaku untuk penulisan lewat ORM; seed script dan perbaikan data
   manual melewatinya, sehingga kolom itu berbohong. Diperbaiki dengan trigger.

3. **Koordinat mustahil diterima** (`latitude = 999` lolos). Ditambahkan CHECK rentang.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (nama index, tabel, kolom FK) — lihat alasan pada docstring butir 1.
_FOREIGN_KEY_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_predictions_baseline_risk_score", "predictions", "baseline_risk_score_id"),
    ("ix_early_warnings_acknowledged_by", "early_warnings", "acknowledged_by"),
    ("ix_early_warnings_resolved_by", "early_warnings", "resolved_by"),
    ("ix_recommendations_warning", "recommendations", "warning_id"),
    ("ix_commander_decisions_decision_by", "commander_decisions", "decision_by"),
    ("ix_operational_actions_location", "operational_actions", "location_id"),
    ("ix_operational_actions_created_by", "operational_actions", "created_by"),
    ("ix_prediction_actual_actual_incident", "prediction_actual", "actual_incident_id"),
    ("ix_prediction_actual_actual_location", "prediction_actual", "actual_location_id"),
    ("ix_role_permissions_permission", "role_permissions", "permission_id"),
)

_SET_UPDATED_AT = """
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

#: Memasang trigger pada setiap tabel yang memiliki kolom updated_at.
#: Tabel baru wajib menambahkannya sendiri — dijaga oleh integration test.
_ATTACH_UPDATED_AT_TRIGGERS = """
DO $$
DECLARE
    target text;
BEGIN
    FOR target IN
        SELECT table_name FROM information_schema.columns
        WHERE table_schema = 'public' AND column_name = 'updated_at'
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%I_set_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            target, target
        );
    END LOOP;
END;
$$;
"""

_DROP_UPDATED_AT_TRIGGERS = """
DO $$
DECLARE
    target text;
BEGIN
    FOR target IN
        SELECT table_name FROM information_schema.columns
        WHERE table_schema = 'public' AND column_name = 'updated_at'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_set_updated_at ON %I', target, target);
    END LOOP;
END;
$$;
"""


def upgrade() -> None:
    for name, table, column in _FOREIGN_KEY_INDEXES:
        op.create_index(name, table, [column])

    op.execute(_SET_UPDATED_AT)
    op.execute(_ATTACH_UPDATED_AT_TRIGGERS)

    for table in ("locations", "citizen_reports"):
        op.create_check_constraint("latitude_range", table, "latitude BETWEEN -90 AND 90")
        op.create_check_constraint("longitude_range", table, "longitude BETWEEN -180 AND 180")


def downgrade() -> None:
    for table in ("locations", "citizen_reports"):
        # Nama pendek: naming convention yang menyusun prefix `ck_<tabel>_`.
        # Menulis nama lengkap menghasilkan prefix ganda (ck_locations_ck_locations_...).
        op.drop_constraint("latitude_range", table, type_="check")
        op.drop_constraint("longitude_range", table, type_="check")

    op.execute(_DROP_UPDATED_AT_TRIGGERS)
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    for name, table, _ in _FOREIGN_KEY_INDEXES:
        op.drop_index(name, table_name=table)
