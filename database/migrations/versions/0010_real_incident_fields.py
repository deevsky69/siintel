"""Kolom yang dibawa data kejadian asli Pusiknas, dan jam kejadian yang boleh kosong.

Keputusan pemilik proyek, 30 September 2026: seluruh data kejadian diganti data asli
(Pusiknas Bareskrim Polri, posisi 29 September 2026; 8.203 Laporan Polisi Curanmor, Curat,
Curas di wilayah Polres Metro Jakarta Selatan, 1 Jan 2023 s.d. 28 Sep 2026).

DUA HAL YANG DIUBAH, DAN MENGAPA KEDUANYA TIDAK BISA DIHINDARI

1. **`incident_time` boleh NULL.** Pada data asli 1.798 kejadian (21,9%) tidak punya jam —
   justru kolom yang kamus datanya tandai SANGAT WAJIB. Memaksa jam palsu (00:00) akan
   menumpuk 1.798 kejadian ke jendela 00:00–06:00 dan merusak pola jam rawan dengan
   tenang. `time_known` menandainya terbuka; `occurred_at` tetap terisi (tengah malam
   setempat) supaya hitungan per hari tidak kehilangan satu pun kejadian, dan kode yang
   membentuk pola jam WAJIB memeriksa `time_known` — dijaga test.

2. **Kolom yang memang dibawa Laporan Polisi** dan selama ini tidak punya tempat:
   kapan dilaporkan (dan jedanya dari kejadian), ke satuan mana, dari sumber apa, nama
   jalan TKP, koordinat bila tercatat (hanya 17%, hampir seluruhnya 2025–2026), grid
   500 m dari sumber, dan kelompok latih/uji yang sudah ditetapkan pemilik data.

   `reported_at` ternyata menentukan: median jeda lapor 4,6 jam, p90 3,4 HARI, maksimum
   hampir dua tahun. Sistem yang berjalan nyata baru tahu sebuah kejadian berhari-hari
   setelahnya — dan evaluasi prediksi-vs-aktual harus jujur soal itu (U-03).

Tidak ada kolom identitas: data sumbernya memang tanpa nama, NIK, telepon, nomor rumah,
RT, maupun RW (CLAUDE.md §16).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATA_GROUPS = ("TRAIN", "TEST")


def upgrade() -> None:
    op.alter_column("crime_incidents", "incident_time", existing_type=sa.Time(), nullable=True)
    op.add_column(
        "crime_incidents",
        sa.Column(
            "time_known",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment=(
                "FALSE bila jam kejadian tidak tercatat; occurred_at lalu berisi "
                "tengah malam setempat."
            ),
        ),
    )
    op.add_column("crime_incidents", sa.Column("reported_at", sa.DateTime(timezone=True)))
    op.add_column(
        "crime_incidents",
        sa.Column("report_lag_hours", sa.Numeric(9, 1), comment="Jeda kejadian → Laporan Polisi."),
    )
    op.add_column("crime_incidents", sa.Column("report_source", sa.String(50)))
    op.add_column("crime_incidents", sa.Column("receiving_unit", sa.String(100)))
    op.add_column(
        "crime_incidents",
        sa.Column(
            "data_group", sa.String(10), comment="TRAIN (laporan 2023-2025) atau TEST (2026)."
        ),
    )
    op.add_column("crime_incidents", sa.Column("street", sa.String(255)))
    op.add_column("crime_incidents", sa.Column("latitude", sa.Numeric(9, 6)))
    op.add_column("crime_incidents", sa.Column("longitude", sa.Numeric(9, 6)))
    op.add_column("crime_incidents", sa.Column("grid_500m", sa.String(20)))
    op.add_column(
        "crime_incidents",
        sa.Column("data_source", sa.String(50), comment="Asal baris, mis. PUSIKNAS-2026-09-29."),
    )
    op.create_check_constraint(
        "data_group_known",
        "crime_incidents",
        "data_group IS NULL OR data_group IN " + str(DATA_GROUPS),
    )
    op.create_check_constraint(
        "time_known_needs_time",
        "crime_incidents",
        "NOT time_known OR incident_time IS NOT NULL",
    )
    op.create_index("ix_crime_incidents_reported_at", "crime_incidents", ["reported_at"])
    op.create_index("ix_crime_incidents_data_group", "crime_incidents", ["data_group"])


def downgrade() -> None:
    op.drop_index("ix_crime_incidents_data_group", table_name="crime_incidents")
    op.drop_index("ix_crime_incidents_reported_at", table_name="crime_incidents")
    op.drop_constraint("time_known_needs_time", "crime_incidents", type_="check")
    op.drop_constraint("data_group_known", "crime_incidents", type_="check")
    for column in (
        "data_source",
        "grid_500m",
        "longitude",
        "latitude",
        "street",
        "data_group",
        "receiving_unit",
        "report_source",
        "report_lag_hours",
        "reported_at",
        "time_known",
    ):
        op.drop_column("crime_incidents", column)
    op.alter_column("crime_incidents", "incident_time", existing_type=sa.Time(), nullable=False)
