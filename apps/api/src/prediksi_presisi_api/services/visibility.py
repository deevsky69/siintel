"""Batas tampilan data kejadian: layar hanya memuat kejadian sampai tanggal tertentu.

Keputusan pemilik proyek 4 Oktober 2026: aplikasi diperagakan seolah berdiri di awal 2026.
Seluruh layar — dashboard, peta, analitik, penilaian, prediksi — hanya boleh melihat
kejadian **sampai 31 Desember 2025**. Kejadian 2026 tetap tersimpan, tetapi hanya dibaca
oleh pencocokan: rencana patroli yang disusun dari pola 2025 dibandingkan dengan kejadian
nyata 2026 (`services/patrol_plan.py`, `services/backtest.py`).

MENGAPA SATU SARINGAN GLOBAL, BUKAN `WHERE` DI 139 TEMPAT

Kejadian dibaca oleh tiga belas modul. Menambahkan `incident_date <= batas` satu per satu
berarti suatu hari ada satu query yang terlewat, dan layar itu diam-diam memperlihatkan
2026 — tanpa ada yang gagal. Saringan ini dipasang pada tingkat ORM lewat
`with_loader_criteria`, sehingga berlaku bagi setiap SELECT yang menyentuh
`CrimeIncident`, termasuk subquery dan join, tanpa satu pun pemanggil perlu mengingatnya.

Yang perlu mengingat justru kebalikannya: modul yang MEMANG harus melihat 2026 menyatakan
itu secara eksplisit (`include_all_incidents`). Itu daftar yang pendek dan sengaja terlihat:
seeder (supaya tidak menggandakan baris yang "tidak terlihat"), evaluasi mundur, dan
pencocokan rencana patroli.

Batasnya konfigurasi (`DISPLAY_DATA_UNTIL`), bukan angka di kode (CLAUDE.md §12). Kosong
berarti tanpa batas — keadaan sebelum 4 Oktober 2026, dan keadaan seluruh test.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from ..config import get_settings
from ..models import CrimeIncident

#: Kunci pada `session.info` ATAU `execution_options` yang mematikan saringan.
INCLUDE_ALL = "include_all_incidents"

DISPLAY_BASIS = (
    "Layar memperlihatkan kejadian sampai DISPLAY_DATA_UNTIL (31 Desember 2025): aplikasi "
    "diperagakan seolah berdiri di awal 2026. Kejadian 2026 tetap tersimpan dan hanya dibaca "
    "oleh pencocokan rencana patroli dan evaluasi mundur."
)

_installed = False


def display_cutoff() -> date | None:
    """Tanggal terakhir yang boleh tampil, atau None bila tanpa batas."""
    raw = get_settings().display_data_until
    if not raw:
        return None
    return date.fromisoformat(raw)


def see_everything(session: Session) -> None:
    """Mematikan saringan untuk seluruh query pada session ini (seeder, evaluasi)."""
    session.info[INCLUDE_ALL] = True


def all_incidents(statement: Any) -> Any:
    """Mematikan saringan untuk SATU statement — bentuk yang terlihat di tempat ia dipakai."""
    return statement.execution_options(**{INCLUDE_ALL: True})


def _apply_cutoff(state: ORMExecuteState) -> None:
    if not state.is_select:
        return
    if state.execution_options.get(INCLUDE_ALL) or state.session.info.get(INCLUDE_ALL):
        return
    cutoff = display_cutoff()
    if cutoff is None:
        return
    state.statement = state.statement.options(
        with_loader_criteria(
            CrimeIncident,
            lambda cls: cls.incident_date <= cutoff,
            include_aliases=True,
        )
    )


def install() -> None:
    """Memasang saringan pada seluruh Session proses ini. Aman dipanggil berulang."""
    global _installed
    if _installed:
        return
    event.listen(Session, "do_orm_execute", _apply_cutoff)
    _installed = True
