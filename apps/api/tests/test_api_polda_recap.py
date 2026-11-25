"""Rekap Polda Metro Jaya per Polres (catatan 196). Angka di sini BUATAN untuk pengujian —
bukan angka Pusiknas."""

from __future__ import annotations

import copy
import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, PoldaRecap, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
URL = "/api/v1/polda/recap"

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


def _unit(name: str, kind: str, overall: tuple[int, int], c3: tuple[int, int, int, int]) -> Any:
    curat, curas, curanmor, cc = c3
    count = {"ct": curat + curas + curanmor, "cc": cc, "curat": curat, "curas": curas}
    return {
        "name": name,
        "kind": kind,
        "overall": {"2032": {"ct": overall[0], "cc": overall[1]}},
        "c3": {"2032": {**count, "curanmor": curanmor}},
        "change_overall": 0.25,
        "change_c3": -0.1,
    }


PAYLOAD: dict[str, Any] = {
    "position_at": "2032-06-30T12:00:00+07:00",
    "source": "Berkas uji buatan",
    "source_sha256": "a" * 64,
    "years": [2032],
    "current_year": 2032,
    "current_until": "2032-06-30",
    "units": [
        _unit("Polres Metro Jakarta Selatan", "POLRES", (100, 10), (20, 5, 15, 4)),
        _unit("Polres Uji Timur", "POLRES", (200, 50), (40, 10, 10, 6)),
        _unit("Ditreskrimum", "SATKER", (50, 25), (1, 0, 0, 1)),
    ],
    "totals": {
        "overall": {"2032": {"ct": 350, "cc": 85}},
        "c3": {"2032": {"ct": 101, "cc": 11, "curat": 61, "curas": 15, "curanmor": 25}},
    },
    "equal_period": None,
    "monthly": [
        {"month": 1, "overall": {"2032": 150}, "c3": {"2032": 51}},
        {"month": 2, "overall": {"2032": 200}, "c3": {"2032": 50}},
    ],
    "settlements": [{"form": "Tahap II / P-21", "counts": {"2032": 9}}],
    "top_types": {"2032": [{"rank": 1, "name": "Penipuan", "ct": 90}]},
}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, session: Session, role_name: str) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, role_name
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_import_then_read_with_derived_figures(client: TestClient, session: Session) -> None:
    admin = _login(client, session, "Administrator")
    kasat = _login(client, session, "Kasat Intelkam")

    imported = client.put(URL, json=PAYLOAD, headers=admin)
    assert imported.status_code == 200, imported.text
    assert imported.json()["units"] == 3 and imported.json()["replaced"] is False
    # Mengirim ulang posisi yang sama mengganti, bukan menggandakan.
    assert client.put(URL, json=PAYLOAD, headers=admin).json()["replaced"] is True
    stored = session.scalars(select(PoldaRecap)).all()
    assert len([row for row in stored if row.source == "Berkas uji buatan"]) == 1

    body = client.get(URL, headers=kasat).json()
    assert body["available"] is True and body["polres_count"] == 2
    assert body["home_unit"] == "Polres Metro Jakarta Selatan"
    units = {unit["name"]: unit for unit in body["units"]}
    home = units["Polres Metro Jakarta Selatan"]
    assert home["home"] is True and home["rank_c3"] == 2 and home["rank_overall"] == 2
    assert home["c3"]["2032"]["ct"] == 40 and home["c3"]["2032"]["cr"] == 10.0
    assert home["c3"]["2032"]["share_pct"] == round(40 / 101 * 100, 2)
    assert home["c3"]["2032"]["of_overall_pct"] == 40.0
    assert home["overall"]["2032"]["cr"] == 10.0 and home["change_overall_pct"] == 25.0
    assert units["Polres Uji Timur"]["rank_c3"] == 1
    # Satuan kerja tingkat Polda tidak diperingkat di antara Polres.
    assert "rank_c3" not in units["Ditreskrimum"]
    assert body["totals"]["overall"]["2032"]["cr"] == round(85 / 350 * 100, 2)
    assert body["totals"]["c3"]["2032"]["of_overall_pct"] == round(101 / 350 * 100, 2)
    assert "bukan data per kejadian" in body["basis"]
    done = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "IMPORT_POLDA_RECAP", AuditLog.result == "SUCCESS"
        )
    )
    assert done is not None


def test_import_is_refused_when_sums_do_not_match(client: TestClient, session: Session) -> None:
    admin = _login(client, session, "Administrator")
    broken = copy.deepcopy(PAYLOAD)
    broken["position_at"] = "2032-07-31T12:00:00+07:00"
    broken["totals"]["overall"]["2032"]["ct"] = 351
    refused = client.put(URL, json=broken, headers=admin)
    assert refused.status_code == 422 and "tidak cocok" in refused.text

    mixed = copy.deepcopy(PAYLOAD)
    mixed["position_at"] = "2032-07-31T12:00:00+07:00"
    mixed["units"][0]["c3"]["2032"]["curat"] = 21  # 21 + 5 + 15 ≠ 40
    assert client.put(URL, json=mixed, headers=admin).status_code == 422

    extra = copy.deepcopy(PAYLOAD)
    extra["nama_pelapor"] = "x"  # kolom di luar skema ditolak, bukan diabaikan
    assert client.put(URL, json=extra, headers=admin).status_code == 400
    assert (
        session.scalar(select(PoldaRecap).where(PoldaRecap.source == "Berkas uji buatan")) is None
    )


def test_only_whole_jurisdiction_analytics_may_read_and_only_admin_imports(
    client: TestClient, session: Session
) -> None:
    kasat = _login(client, session, "Kasat Intelkam")
    polsek = _login(client, session, "Polsek")
    humas = _login(client, session, "Humas")
    # Hanya Administrator (config:manage) yang memasukkan data.
    assert client.put(URL, json=PAYLOAD, headers=kasat).status_code == 403
    # Polsek punya analytics:read sebatas wilayahnya; Humas tidak punya sama sekali.
    assert client.get(URL, headers=polsek).status_code == 403
    assert client.get(URL, headers=humas).status_code == 403
    assert client.get(URL).status_code == 401
    denied = session.scalar(
        select(AuditLog).where(AuditLog.action == "READ_POLDA_RECAP", AuditLog.result == "DENIED")
    )
    assert denied is not None
    # Sebelum ada data: tersedia = salah, bukan galat.
    session.query(PoldaRecap).delete()
    assert client.get(URL, headers=kasat).json()["available"] is False
