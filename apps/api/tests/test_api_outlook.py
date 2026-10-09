"""Perkiraan bulan ke depan (`services/outlook.py`) dan ekspor .docx-nya."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import outlook, visibility

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
CUTOFF = date(2098, 12, 31)


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    visibility.install()
    monkeypatch.setattr(visibility, "display_cutoff", lambda: CUTOFF)
    db = create_engine(DATABASE_URL, future=True)
    connection = db.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    db.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _plant(session: Session, location: Location, day: date, hour: int, count: int) -> None:
    for _ in range(count):
        session.add(
            CrimeIncident(
                code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
                incident_type="CURANMOR",
                occurred_at=datetime.combine(day, time(hour=hour), tzinfo=UTC),
                incident_date=day,
                incident_time=time(hour=hour),
                time_known=True,
                location_id=location.location_id,
                data_source="UJI",
            )
        )
    session.flush()


def test_outlook_uses_the_same_month_of_previous_years(session: Session) -> None:
    rows = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    ).all()
    hot, cold = rows[0], rows[1]
    # Maret 2097 dan Maret 2098 ramai di `hot` pukul 20; April tidak boleh ikut.
    _plant(session, hot, date(2097, 3, 10), 20, 2)
    _plant(session, hot, date(2098, 3, 12), 19, 2)  # blok 18-21 juga
    _plant(session, hot, date(2098, 4, 1), 20, 5)  # bulan lain
    _plant(session, cold, date(2098, 3, 3), 2, 1)

    result = outlook.build_outlook(session, 2099, 3, None)
    assert result["target_month"] == "2099-03" and result["status"] == "PROPOSED"
    assert "2098-03" in result["basis_months"] and "2097-03" in result["basis_months"]
    curanmor = next(t for t in result["threats"] if t["threat_type"] == "CURANMOR")
    assert curanmor["basis_incidents"] == 5  # 2 + 2 + 1, tanpa April
    top = curanmor["slots"][0]
    assert top["kelurahan"] == hot.kelurahan and top["block_label"] == "18.00-21.00"
    assert top["incidents"] == 4
    assert "SAMAPTA" in top["recommendation"] and hot.kelurahan in top["recommendation"]
    assert curanmor["peak_block"] == "18.00-21.00"


def test_docx_export_is_a_word_document(client: TestClient, session: Session) -> None:
    role = session.scalar(select(Role).where(Role.role_name == "Pimpinan"))
    assert role is not None
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
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/patrol-plan/outlook").status_code == 401
    as_json = client.get("/api/v1/patrol-plan/outlook?month=2099-03", headers=headers)
    assert as_json.status_code == 200 and as_json.json()["target_label"] == "Maret 2099"

    as_docx = client.get("/api/v1/patrol-plan/outlook?month=2099-03&format=docx", headers=headers)
    assert as_docx.status_code == 200
    assert as_docx.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "perkiraan-kerawanan-2099-03.docx" in as_docx.headers["content-disposition"]
    assert as_docx.content[:2] == b"PK"  # berkas .docx adalah arsip zip
