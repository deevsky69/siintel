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

#: Jalur menuju wilayah. Seluruhnya bermuara pada `locations.polsek`.
JURISDICTION_PATH: dict[str, tuple[str, str]] = {
    resource: ("locations", "polsek")
    for resource in (
        "dashboard",
        "crime",
        "intelligence",
        "patrol",
        "police_unit",
        "map",
        "analytics",
        "risk_score",
        "prediction",
        "warning",
        "public_alert",
        "recommendation",
        "commander_decision",
        "operation",
        "citizen_report",
        "community_feedback",
        "evaluation",
        "audit",
        "location",
    )
}


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
