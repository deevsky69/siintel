"""Modul 4 mekanisme, dua tahap (10 November 2026): draf membekukan peringkat → analis memeriksa
dan mengirim → Pimpinan menetapkan → pelaksanaan; alasan wajib dan kewenangan per peran (1B)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, MonthlyProduct, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
MONTH = "2032-03"
BASE = "/api/v1/monthly-products"


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


def _login(
    client: TestClient, session: Session, role_name: str, polsek: str | None = None
) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, role_name
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        polsek=polsek,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed(session: Session) -> Location:
    area = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.kelurahan)
    )
    assert area is not None
    for i in range(5):
        day = date(2032, 1, 4) + timedelta(days=i * 7)
        session.add(
            CrimeIncident(
                code=f"INC-UJI-{uuid.uuid4().hex[:8]}",
                incident_type="CURANMOR",
                occurred_at=datetime.combine(day, time(22, 0), tzinfo=clock.JAKARTA),
                incident_date=day,
                incident_time=time(22, 0),
                time_known=True,
                location_id=area.location_id,
                reported_at=datetime.combine(day, time(23, 0), tzinfo=clock.JAKARTA),
                vehicle_object=True,
                status="REPORTED",
            )
        )
    session.flush()
    return area


def _post(client: TestClient, path: str, body: dict[str, Any], headers: dict[str, str]) -> Any:
    return client.post(f"{BASE}/{MONTH}/{path}", json=body, headers=headers)


def test_full_chain_from_draft_to_recorded_action(client: TestClient, session: Session) -> None:
    area = _seed(session)
    admin = _login(client, session, "Administrator")
    analyst = _login(client, session, "Analis Intelkam")
    leader = _login(client, session, "Pimpinan")
    polsek_in = _login(client, session, "Polsek", polsek=area.polsek)

    # Peran Kasat Intelkam tidak ada lagi (0023); Pimpinan tidak menyusun draf.
    assert session.scalar(select(Role).where(Role.role_name == "Kasat Intelkam")) is None
    assert client.post(BASE, json={"month": MONTH}, headers=leader).status_code == 403

    # "Susun" membekukan peringkat bulan itu sekaligus — tidak ada langkah terpisah.
    assert client.get(f"/api/v1/rankings?month={MONTH}", headers=analyst).json()["frozen"] is False
    created = client.post(BASE, json={"month": MONTH}, headers=analyst)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "DRAFT" and body["next_stage"] == "ANALYST"
    assert body["facts"]["ranking_frozen_by_draft"] is True
    assert client.get(f"/api/v1/rankings?month={MONTH}", headers=analyst).json()["frozen"] is True
    assert body["items"][0]["kelurahan"] == area.kelurahan
    assert body["items"][0]["pattern"]["dominant_threat"] == "CURANMOR"
    assert body["items"][0]["pattern"]["peak_block_label"] == "21.00-24.00"
    assert client.post(BASE, json={"month": MONTH}, headers=admin).status_code == 409

    # Analis: tolak tanpa alasan ditolak; dengan alasan diterima → langsung menunggu Pimpinan.
    second = body["items"][1]["kelurahan"]
    bad = _post(
        client, "analyst", {"items": [{"kelurahan": second, "status": "REJECTED"}]}, analyst
    )
    assert bad.status_code == 400
    assert (
        _post(client, "decide", {"selected": [{"kelurahan": area.kelurahan}]}, leader).status_code
        == 409
    )
    reviewed = _post(
        client,
        "analyst",
        {
            "items": [
                {
                    "kelurahan": area.kelurahan,
                    "status": "REVISED",
                    "text": "Koordinasi pengelola parkir",
                    "reason": "laporan Babin: parkir liar",
                },
                {"kelurahan": second, "status": "REJECTED", "reason": "tidak didukung lapangan"},
            ],
            "note": "diperiksa 10 Nov",
        },
        analyst,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "ANALYST_REVIEWED"
    assert reviewed.json()["next_stage"] == "PIMPINAN"
    assert reviewed.json()["awaiting_decision"] is True
    assert reviewed.json()["items"][1]["analyst_status"] == "REJECTED"

    # Tahap KBO dan Kasat tidak ada lagi.
    assert _post(client, "kbo", {"outcome": "ACCEPTED"}, analyst).status_code == 404
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, leader).status_code == 404

    # Pimpinan menetapkan: yang ditolak analis tidak dapat dipilih; Admin dan Analis tidak boleh.
    pick = {"selected": [{"kelurahan": area.kelurahan}]}
    assert _post(client, "decide", pick, admin).status_code == 403
    assert _post(client, "decide", pick, analyst).status_code == 403
    assert _post(client, "decide", {"selected": [{"kelurahan": second}]}, leader).status_code == 400
    decided = _post(
        client,
        "decide",
        {
            "selected": [{"kelurahan": area.kelurahan, "action": "Patroli malam dan parkir"}],
            "reason": "sumber daya tersedia",
        },
        leader,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "DECIDED" and decided.json()["priority_count"] == 1
    chosen = decided.json()["items"][0]
    assert chosen["selected"] is True and chosen["decided_action"].startswith("Patroli")
    stages = [s["stage"] for s in decided.json()["stages"]]
    assert stages == ["ANALYST", "PIMPINAN"]

    # Pelaksanaan: Polsek wilayah mencatat; Polsek lain 404; bukan prioritas 404.
    action = {
        "acted_at": "2032-03-05T21:00:00+07:00",
        "place": "Parkiran pasar",
        "action": "Patroli dan penjagaan",
        "result": "aman",
    }
    other = _login(client, session, "Polsek", polsek="Polsek Lain Uji")
    path = f"items/{area.kelurahan}/actions"
    assert _post(client, path, action, other).status_code == 404
    assert _post(client, f"items/{second}/actions", action, polsek_in).status_code == 404
    recorded = _post(client, path, action, polsek_in)
    assert recorded.status_code == 201, recorded.text
    assert recorded.json()["unit"] == area.polsek

    final = client.get(f"{BASE}/{MONTH}", headers=leader).json()
    assert len(final["items"][0]["actions"]) == 1
    months = [row["target_month"] for row in client.get(BASE, headers=leader).json()["data"]]
    assert MONTH in months


def test_product_left_in_a_retired_status_can_still_be_decided(
    client: TestClient, session: Session
) -> None:
    """Produk yang tertahan di KBO_CHECKED/VALIDATED (alur lama) tidak boleh terkunci."""
    area = _seed(session)
    analyst = _login(client, session, "Analis Intelkam")
    leader = _login(client, session, "Pimpinan")
    assert client.post(BASE, json={"month": MONTH}, headers=analyst).status_code == 201
    product = session.scalar(select(MonthlyProduct))
    assert product is not None
    product.status = "VALIDATED"
    session.flush()
    shown = client.get(f"{BASE}/{MONTH}", headers=leader).json()
    assert shown["awaiting_decision"] is True and shown["next_stage"] == "PIMPINAN"
    decided = _post(client, "decide", {"selected": [{"kelurahan": area.kelurahan}]}, leader)
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "DECIDED"
