"""Tabel "bila ambang dinaikkan" (`GET /evaluation/threshold-sweep`) dan batas tampilan
pada ringkasan dashboard.

Keduanya bahan keputusan, bukan klaim: tabel ambang dihitung ulang dari baris evaluasi yang
tersimpan tanpa membuat prediksi baru, dan dashboard menyebut sampai tanggal berapa layar
memuat kejadian.
"""

from __future__ import annotations

import itertools
import os
import uuid
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import risk_engine as risk
from prediksi_presisi_api.services import visibility

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


def _headers(client: TestClient, session: Session, role_name: str = "Pimpinan") -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
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
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_the_sweep_starts_at_the_floor_in_force_and_only_ever_loses_recall(
    client: TestClient, session: Session
) -> None:
    body = client.get(
        "/api/v1/evaluation/threshold-sweep", headers=_headers(client, session)
    ).json()
    floor = risk.load_thresholds().minimum_warning_score
    assert body["current_floor"] == floor
    assert body["status"] == "PROPOSED" and "basis" in body
    rows = body["rows"]
    assert rows[0]["threshold"] == floor
    assert rows[-1]["threshold"] == 95
    # Baris pertama tidak membuat prediksi baru: yang ia hitung adalah baris evaluasi yang
    # tersimpan, dengan HIT berskor di bawah ambang berpindah menjadi luput. Jumlah
    # kejadian nyata (HIT + FN) karena itu tidak pernah berubah terhadap angka utama.
    metrics = client.get("/api/v1/evaluation/metrics", headers=_headers(client, session)).json()
    assert rows[0]["hits"] <= metrics["hits"]
    assert (
        rows[0]["hits"] + rows[0]["false_negatives"] == metrics["hits"] + metrics["false_negatives"]
    )
    # Menaikkan ambang hanya dapat mengurangi yang terbit dan menambah yang luput.
    for earlier, later in itertools.pairwise(rows):
        assert (
            later["hits"] + later["false_positives"] <= earlier["hits"] + earlier["false_positives"]
        )
        assert later["false_negatives"] >= earlier["false_negatives"]
        assert (
            later["hits"] + later["false_negatives"] == earlier["hits"] + earlier["false_negatives"]
        )


def test_the_sweep_requires_the_evaluation_permission(client: TestClient, session: Session) -> None:
    response = client.get(
        "/api/v1/evaluation/threshold-sweep", headers=_headers(client, session, "Polsek")
    )
    assert response.status_code in (200, 403)


def test_the_dashboard_states_the_display_cutoff(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, session)
    assert (
        client.get("/api/v1/dashboard/summary", headers=headers).json()["display_data_until"]
        is None
    )
    monkeypatch.setattr(visibility, "display_cutoff", lambda: date(2025, 12, 31))
    body = client.get("/api/v1/dashboard/summary", headers=headers).json()
    assert body["display_data_until"] == "2025-12-31"
