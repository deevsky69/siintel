"""Daftar rekomendasi membawa apa/di mana/kapan/skor dari prediksinya (7 Oktober 2026)."""

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
from prediksi_presisi_api.models import Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


@pytest.fixture
def session() -> Iterator[Session]:
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


def test_rows_carry_what_where_when_and_score(client: TestClient, session: Session) -> None:
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
    body = client.get(
        "/api/v1/recommendations?page_size=5", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert body["data"], "fixture tanpa rekomendasi"
    for row in body["data"]:
        assert {"threat_type", "time_window", "risk_score", "kecamatan", "kelurahan"} <= set(row)
        assert 0 <= row["risk_score"] <= 100
        assert row["kecamatan"]
