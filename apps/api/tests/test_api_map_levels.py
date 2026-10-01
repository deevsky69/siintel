"""Layer peta setingkat kelurahan (`level=kelurahan`).

Sejak data asli Pusiknas sel master lokasi adalah kelurahan. Ketiga layer harus dapat
dikelompokkan per kelurahan di dalam satu kecamatan, dan angkanya harus menjumlah kembali
ke baris kecamatan yang sama — kalau tidak, peta yang diperbesar menceritakan hal lain
daripada peta yang diperkecil.
"""

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


def _headers(client: TestClient, session: Session) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == "Administrator"))
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


@pytest.mark.parametrize(
    ("path", "measure"),
    [
        ("/api/v1/map/current-risk", "cell_count"),
        ("/api/v1/map/predictive-heatmap?horizon=24H", "cell_count"),
        ("/api/v1/map/historical?months=36", "incidents"),
    ],
)
def test_kelurahan_rows_add_up_to_their_kecamatan(
    client: TestClient, session: Session, path: str, measure: str
) -> None:
    headers = _headers(client, session)
    joiner = "&" if "?" in path else "?"
    coarse = client.get(path, headers=headers).json()
    assert coarse["level"] == "kecamatan"
    assert coarse["areas"], "fixture tidak memuat satu pun wilayah"
    kecamatan = coarse["areas"][0]["kecamatan"]
    assert all(area["kelurahan"] is None for area in coarse["areas"])

    fine = client.get(
        f"{path}{joiner}level=kelurahan&kecamatan={kecamatan}", headers=headers
    ).json()
    assert fine["level"] == "kelurahan" and fine["kecamatan"] == kecamatan
    assert fine["areas"], "kecamatan tanpa satu pun baris kelurahan"
    assert {area["kecamatan"] for area in fine["areas"]} == {kecamatan}

    expected = next(area for area in coarse["areas"] if area["kecamatan"] == kecamatan)[measure]
    assert sum(area[measure] for area in fine["areas"]) == expected, (
        "peta yang diperbesar harus menjumlah kembali ke baris kecamatannya"
    )


def test_cells_without_a_kelurahan_are_returned_not_dropped(
    client: TestClient, session: Session
) -> None:
    """Sel cadangan setingkat kecamatan (kelurahan null) tetap ikut, supaya angkanya tidak
    menguap saat peta diperbesar. Fixture sampel mungkin tidak memilikinya; yang dijaga di
    sini adalah bentuk responsnya, bukan ada tidaknya sel semacam itu."""
    headers = _headers(client, session)
    body = client.get("/api/v1/map/current-risk?level=kelurahan", headers=headers).json()
    assert "level_basis" in body
    for area in body["areas"]:
        assert "kelurahan" in area


def test_an_unknown_level_is_refused(client: TestClient, session: Session) -> None:
    headers = _headers(client, session)
    response = client.get("/api/v1/map/current-risk?level=rt", headers=headers)
    assert response.status_code == 400, response.text
