"""Setiap cakupan yang dideklarasikan harus benar-benar dapat ditegakkan.

`config/rbac/permissions.yaml` menyatakan peran Fungsi dibatasi `OWN_FUNCTION` untuk
`crime:read`, padahal `crime_incidents` tidak memiliki kolom fungsi sama sekali — akun
Fungsi tetap melihat seluruh 1200 kejadian. Cacat itu tidak terlihat oleh satu pun test:
seluruhnya menguji apa yang **ditolak**, bukan apa yang **dijanjikan tetapi tidak
pernah ditegakkan**.

Kewenangan yang dideklarasikan tanpa dapat ditegakkan lebih berbahaya daripada yang
tidak dideklarasikan, sebab ia memberi rasa aman yang keliru kepada pembaca dokumen
kewenangan.

Test ini memeriksa jalur penyaringannya **ke katalog PostgreSQL**, bukan ke daftar yang
diketik ulang di sini — sehingga menghapus sebuah kolom akan menggagalkannya.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.seeding.paths import RBAC_FILE

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)

#: Bagaimana tiap resource dapat ditelusuri sampai ke sebuah fungsi. Nilainya adalah
#: (tabel, kolom) terakhir pada jalur itu; keberadaannya diperiksa ke database.
FUNCTION_PATH: dict[str, tuple[str, str]] = {
    "recommendation": ("recommendations", "recommended_function"),
    # commander_decisions -> recommendations.recommended_function
    "commander_decision": ("recommendations", "recommended_function"),
    # operational_actions.unit_id -> police_units.function
    "operation": ("police_units", "function"),
    # patrol_activity.unit_id -> police_units.function
    "patrol": ("police_units", "function"),
    "police_unit": ("police_units", "function"),
}

#: Jalur menuju wilayah, per resource — bukan satu asumsi untuk semuanya.
#:
#: Versi pertama memetakan SELURUH resource ke `("locations", "polsek")` dan hanya
#: memeriksa bahwa kolom itu ada. Pemeriksaan seperti itu lulus untuk apa pun, sehingga
#: memberi rasa aman tanpa memeriksa apa pun — persis cacat yang seharusnya ia tangkap.
#: `public_alerts` lolos begitu saja meski tabelnya tidak punya kolom lokasi sama sekali.
JURISDICTION_PATH: dict[str, tuple[str, str]] = {
    # Kolom lokasi langsung pada tabelnya.
    "crime": ("crime_incidents", "location_id"),
    "intelligence": ("intelligence_reports", "location_id"),
    "patrol": ("patrol_activity", "location_id"),
    "risk_score": ("risk_scores", "location_id"),
    "prediction": ("predictions", "location_id"),
    "warning": ("early_warnings", "location_id"),
    "operation": ("operational_actions", "location_id"),
    "citizen_report": ("citizen_reports", "location_id"),
    "location": ("locations", "polsek"),
    # Kolom wilayahnya sendiri, bukan lewat `locations`.
    "police_unit": ("police_units", "jurisdiction"),
    # Lewat rantai: recommendations -> predictions.location_id -> locations.polsek
    "recommendation": ("predictions", "location_id"),
    # commander_decisions -> recommendations -> predictions -> locations
    "commander_decision": ("predictions", "location_id"),
    # Dua lompatan. Sempat saya kira keduanya tidak dapat ditelusuri karena tabelnya
    # sendiri tidak punya kolom lokasi — keliru, dan kekeliruan itu sempat melebarkan
    # kewenangan Polsek atas nama koreksi. Yang menangkapnya adalah test perilaku
    # `test_feedback_block_follows_its_own_permission`, bukan pemeriksaan ini.
    #   public_alerts.warning_id     -> early_warnings.location_id
    "public_alert": ("early_warnings", "location_id"),
    #   community_feedback.report_id -> citizen_reports.location_id
    "community_feedback": ("citizen_reports", "location_id"),
}

#: Resource yang bukan tabel melainkan **pandangan agregat** atas data yang sudah
#: tersaring. Cakupannya ditegakkan di endpoint masing-masing lewat `jurisdiction_filter`,
#: bukan lewat sebuah kolom. Didaftar terpisah supaya pengecualiannya menjadi keputusan
#: sadar, bukan lubang pada pemeriksaan.
JURISDICTION_AGGREGATES = frozenset({"dashboard", "map", "analytics", "evaluation"})


@pytest.fixture(scope="module")
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    opened = sessionmaker(bind=engine)()
    yield opened
    opened.close()
    engine.dispose()


def _grants() -> dict[str, dict[str, list[str]]]:
    catalog: dict[str, Any] = yaml.safe_load(RBAC_FILE.read_text())
    roles: dict[str, dict[str, list[str]]] = catalog["roles"]
    return roles


def _column_exists(session: Session, table: str, column: str) -> bool:
    return bool(
        session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        ).first()
    )


def _scoped(scope: str) -> list[tuple[str, str]]:
    return [
        (role, permission)
        for role, grants in _grants().items()
        for granted_scope, permissions in grants.items()
        if granted_scope == scope
        for permission in permissions
    ]


def test_every_own_function_permission_has_a_path_to_a_function(session: Session) -> None:
    unroutable: list[str] = []

    for role, permission in _scoped("OWN_FUNCTION"):
        resource = permission.split(":", 1)[0]
        path = FUNCTION_PATH.get(resource)
        if path is None or not _column_exists(session, *path):
            unroutable.append(f"{role}/{permission}")

    assert not unroutable, (
        "permission berikut dinyatakan OWN_FUNCTION tetapi datanya tidak punya jalur "
        f"menuju sebuah fungsi, sehingga cakupannya mustahil ditegakkan: {unroutable}"
    )


def test_every_own_jurisdiction_permission_has_a_path_to_a_polsek(session: Session) -> None:
    unroutable: list[str] = []

    for role, permission in _scoped("OWN_JURISDICTION"):
        resource = permission.split(":", 1)[0]
        if resource in JURISDICTION_AGGREGATES:
            continue
        path = JURISDICTION_PATH.get(resource)
        if path is None or not _column_exists(session, *path):
            unroutable.append(f"{role}/{permission}")

    assert not unroutable, (
        "permission berikut dinyatakan OWN_JURISDICTION tetapi tidak dapat ditelusuri "
        f"sampai ke sebuah polsek: {unroutable}"
    )


def test_the_check_would_catch_a_regression(session: Session) -> None:
    """Tanpa ini, kedua test di atas dapat lulus karena pemeriksanya sendiri rusak."""
    # `crime_incidents` sengaja dipakai: inilah tabel yang dahulu dinyatakan OWN_FUNCTION.
    assert not _column_exists(session, "crime_incidents", "function")
    assert _column_exists(session, "police_units", "function")
    assert "crime" not in FUNCTION_PATH, (
        "crime_incidents tidak punya kolom fungsi; memasukkannya ke FUNCTION_PATH "
        "akan membuat pemeriksaan ini meluluskan cakupan yang tidak dapat ditegakkan"
    )

    # Ketiganya tidak punya jalur ke wilayah sama sekali. Bila kelak salah satu masuk
    # ke JURISDICTION_PATH tanpa kolom yang benar-benar ada, pemeriksaan di atas kembali
    # menjadi hiasan.
    # Ketiganya tidak punya kolom lokasi pada tabelnya sendiri. Dua di antaranya tetap
    # dapat ditelusuri lewat lompatan berikutnya — dan menyimpulkan sebaliknya dari
    # ketiadaan kolom langsung adalah kekeliruan yang pernah terjadi.
    for table in ("public_alerts", "community_feedback", "audit_logs"):
        assert not _column_exists(session, table, "location_id")
    assert _column_exists(session, "public_alerts", "warning_id")
    assert _column_exists(session, "community_feedback", "report_id")
    # `audit_logs` benar-benar buntu: tidak ada kolom apa pun yang menuntun ke wilayah.
    assert "audit" not in JURISDICTION_PATH
