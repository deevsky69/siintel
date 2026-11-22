"""Kalender SOP (catatan 192): butir berkala SOP dicatat pejabat yang berwenang; butir yang
diketahui sistem tidak dapat dicentang tangan; rekap triwulan dihitung dari catatan Evaluasi."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, Role, SopCheck, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
PERIOD = "2033-05"
URL = "/api/v1/sop/calendar"

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


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


def _items(body: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = body["items"]
    assert isinstance(rows, list)
    return {str(row["key"]): row for row in rows}


def test_calendar_lists_the_periodic_sop_items_with_facts(
    client: TestClient, session: Session
) -> None:
    kbo = _login(client, session, "KBO")
    response = client.get(URL, params={"period": PERIOD}, headers=kbo)
    assert response.status_code == 200, response.text
    body = response.json()
    items = _items(body)
    assert set(items) == {
        "data_received", "data_checked", "ranking_frozen", "product_validated",
        "evaluation_done", "access_log_reviewed", "backup_checked", "quarterly_report",
    }  # fmt: skip
    assert body["period"] == PERIOD and body["total"] == 8 and body["done"] == 0
    assert all(row["fact"] for row in items.values())
    # KBO mencatat butir data dan evaluasi, bukan butir keamanan atau laporan triwulan.
    assert items["data_received"]["can_record"] is True
    assert items["access_log_reviewed"]["can_record"] is False
    assert items["quarterly_report"]["can_record"] is False
    assert items["ranking_frozen"]["source"] == "SYSTEM"
    assert items["ranking_frozen"]["can_record"] is False
    # Triwulan II 2033, belum ada produk yang dicatat.
    assert body["quarter"]["label"] == "Triwulan 2 2033"
    assert body["quarter"]["months"] == ["2033-04", "2033-05", "2033-06"]
    assert body["quarter"]["recorded"] == 0 and body["quarter"]["median_quality_sigap"] is None


def test_only_the_authorised_role_records_an_item_and_only_once(
    client: TestClient, session: Session
) -> None:
    kbo = _login(client, session, "KBO")
    kasat = _login(client, session, "Kasat Intelkam")
    leader = _login(client, session, "Pimpinan")

    # Kasat tidak mencatat butir KBO; penolakannya meninggalkan jejak audit.
    refused = client.post(f"{URL}/{PERIOD}/data_received", json={}, headers=kasat)
    assert refused.status_code == 403
    denied = session.scalar(
        select(AuditLog).where(AuditLog.action == "RECORD_SOP_CHECK", AuditLog.result == "DENIED")
    )
    assert denied is not None and denied.resource_id == f"{PERIOD}:data_received"

    recorded = client.post(
        f"{URL}/{PERIOD}/data_received", json={"note": "diterima dari 10 Polsek"}, headers=kbo
    )
    assert recorded.status_code == 201, recorded.text
    row = _items(recorded.json())["data_received"]
    assert row["done"] is True and row["done_by"] and row["note"] == "diterima dari 10 Polsek"
    assert row["can_record"] is False
    assert recorded.json()["done"] == 1
    assert client.post(f"{URL}/{PERIOD}/data_received", json={}, headers=kbo).status_code == 409

    # Butir keamanan dicatat pemegang Audit Log; laporan triwulan oleh Kasat Intelkam.
    assert (
        client.post(f"{URL}/{PERIOD}/access_log_reviewed", json={}, headers=kbo).status_code == 403
    )
    assert (
        client.post(f"{URL}/{PERIOD}/access_log_reviewed", json={}, headers=leader).status_code
        == 201
    )
    assert (
        client.post(f"{URL}/{PERIOD}/quarterly_report", json={}, headers=kasat).status_code == 201
    )
    stored = session.scalars(select(SopCheck).where(SopCheck.period == PERIOD)).all()
    assert {check.item for check in stored} == {
        "data_received", "access_log_reviewed", "quarterly_report",
    }  # fmt: skip


def test_system_items_and_unknown_items_cannot_be_ticked(
    client: TestClient, session: Session
) -> None:
    admin = _login(client, session, "Administrator")
    # Diturunkan dari sistem: bahkan Administrator tidak dapat mencentangnya.
    assert client.post(f"{URL}/{PERIOD}/ranking_frozen", json={}, headers=admin).status_code == 409
    assert (
        client.post(f"{URL}/{PERIOD}/product_validated", json={}, headers=admin).status_code == 409
    )
    assert client.post(f"{URL}/{PERIOD}/tidak_ada", json={}, headers=admin).status_code == 404
    assert client.post(f"{URL}/2033-13/data_received", json={}, headers=admin).status_code == 400
    assert client.get(URL, params={"period": PERIOD}).status_code == 401
