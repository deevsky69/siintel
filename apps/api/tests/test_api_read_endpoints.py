"""Test endpoint baca dan penegakan cakupan (TASK 031–040, 070).

Yang paling penting di sini bukan bentuk responsnya, melainkan bahwa **cakupan benar-benar
ditegakkan di backend**: pengguna ber-scope `OWN_JURISDICTION` tidak menerima baris di luar
wilayahnya, bahkan tidak dalam jumlah total pada pagination.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


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


def _make_user(session: Session, role_name: str, polsek: str | None = None) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None

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
    return user


def _token(client: TestClient, user: User) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def _auth(client: TestClient, user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(client, user)}"}


def test_leader_sees_every_incident(client: TestClient, session: Session) -> None:
    """Pimpinan melihat seluruh kejadian yang ada, berapa pun jumlahnya.

    Jumlahnya dibandingkan dengan hitungan basis data, bukan dengan angka tetap:
    sejak `/input` ada, kejadian bertambah lewat layar dan angka tetap apa pun akan
    usang. Yang diuji adalah **tidak ada penyaringan**, bukan besarnya dataset.
    """
    leader = _make_user(session, "Pimpinan")
    everything = session.scalar(select(func.count()).select_from(CrimeIncident)) or 0

    response = client.get("/api/v1/crimes?page_size=1", headers=_auth(client, leader))

    assert response.status_code == 200
    assert response.json()["pagination"]["total_items"] == everything


def test_polsek_user_only_sees_its_own_jurisdiction(client: TestClient, session: Session) -> None:
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    response = client.get("/api/v1/crimes?page_size=200", headers=_auth(client, officer))

    assert response.status_code == 200
    body = response.json()
    everything = session.scalar(select(func.count()).select_from(CrimeIncident)) or 0
    assert body["pagination"]["total_items"] < everything
    assert {row["polsek"] for row in body["data"]} == {polsek}


def test_scoped_user_without_a_jurisdiction_is_refused(
    client: TestClient, session: Session
) -> None:
    # Cakupan terbatas tanpa penetapan wilayah harus menutup, bukan berubah jadi akses penuh.
    officer = _make_user(session, "Polsek", polsek=None)

    response = client.get("/api/v1/crimes", headers=_auth(client, officer))

    assert response.status_code == 403


def test_missing_permission_is_denied_and_recorded(client: TestClient, session: Session) -> None:
    # Role tanpa permission apa pun: menguji jalur penolakan, bukan endpoint tertentu.
    empty_role = Role(
        code=f"ROLE-UJI-{uuid.uuid4().hex[:4]}", role_name=f"Uji {uuid.uuid4().hex[:4]}", level=6
    )
    session.add(empty_role)
    session.flush()
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=empty_role.role_id,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()

    response = client.get("/api/v1/crimes", headers=_auth(client, user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    denied = session.scalars(
        select(AuditLog).where(AuditLog.result == "DENIED", AuditLog.user_id == user.user_id)
    ).all()
    assert denied, "penolakan otorisasi harus meninggalkan jejak audit"


def test_predictions_always_carry_their_explanation(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Administrator")

    response = client.get("/api/v1/predictions?page_size=5", headers=_auth(client, analyst))

    assert response.status_code == 200
    for row in response.json()["data"]:
        assert row["dominant_factors"], row["code"]
        # `source` wajib ikut agar hasil aturan tidak terbaca sebagai temuan model.
        assert all(item["source"] in {"RULE", "MODEL"} for item in row["dominant_factors"])


def test_prediction_filter_by_horizon(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Administrator")

    response = client.get("/api/v1/predictions?horizon=6H", headers=_auth(client, analyst))

    assert response.status_code == 200
    assert {row["forecast_horizon"] for row in response.json()["data"]} == {"6H"}


def test_dashboard_summary_is_computed_from_the_database(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/dashboard/summary", headers=_auth(client, leader))

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["security_index"] <= 100
    assert body["top_threats"]
    assert body["risk_by_district"]
    # Angka indeks tidak boleh tampil tanpa penjelasan asalnya.
    assert "belum ditetapkan" in body["security_index_basis"]


def test_dashboard_states_when_a_reference_clock_is_used(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/dashboard/summary", headers=_auth(client, leader))

    # Pembaca layar harus tahu bahwa "24 jam terakhir" dihitung terhadap waktu acuan.
    assert "demo_clock" in response.json()
    assert "reference_time" in response.json()


def test_evaluation_metrics_are_marked_as_proposed(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Administrator")

    response = client.get("/api/v1/evaluation/metrics", headers=_auth(client, analyst))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PROPOSED"
    assert "U-03" in body["basis"]
    assert body["recall"] is not None, "recall harus dapat dihitung sejak TASK 023"


def test_pagination_envelope_follows_the_contract(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/crimes?page=2&page_size=10", headers=_auth(client, leader))

    body = response.json()
    assert set(body) == {"data", "pagination"}
    assert body["pagination"]["page"] == 2
    assert body["pagination"]["page_size"] == 10
    assert len(body["data"]) == 10


def test_page_size_is_capped(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/crimes?page_size=5000", headers=_auth(client, leader))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_police_units_are_listed_for_assignment(client: TestClient, session: Session) -> None:
    centre = _make_user(session, "Administrator")

    response = client.get("/api/v1/police-units", headers=_auth(client, centre))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"], "tidak ada satuan yang dapat ditugaskan"
    assert {"code", "unit_name", "function", "jurisdiction", "status"} <= set(body["data"][0])
    # Cara penyaringan dinyatakan, bukan menjadi perilaku tersembunyi.
    assert body["scope_basis"]


def test_police_units_keep_polres_level_units_visible_to_a_polsek(
    client: TestClient, session: Session
) -> None:
    """Satuan tingkat Polres tetap terlihat oleh pengguna polsek.

    Menyaring dengan pencocokan tepat pada `jurisdiction` akan menyembunyikannya —
    padahal satuan tingkat Polres justru bertugas melintasi seluruh polsek, termasuk
    wilayah pengguna itu. Menyembunyikannya membuat petugas mengira satuan itu tidak ada.
    """
    polsek = session.scalar(select(Location.polsek).where(Location.polsek.is_not(None)).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=str(polsek))
    centre = _make_user(session, "Administrator")

    scoped = client.get("/api/v1/police-units", headers=_auth(client, officer)).json()["data"]
    everything = client.get("/api/v1/police-units", headers=_auth(client, centre)).json()["data"]

    assert scoped, "pengguna polsek tidak menerima satu pun satuan"
    assert len(scoped) < len(everything), "cakupan wilayah tidak ditegakkan"

    known = set(
        session.scalars(
            select(Location.polsek).where(Location.polsek.is_not(None)).distinct()
        ).all()
    )
    for unit in scoped:
        # Entah satuan milik polseknya, entah satuan lintas polsek — tidak ada yang lain.
        assert unit["jurisdiction"] == polsek or unit["jurisdiction"] not in known

    assert any(unit["jurisdiction"] not in known for unit in scoped), (
        "tidak ada satuan tingkat Polres yang lolos — penyaringan terlalu ketat"
    )
