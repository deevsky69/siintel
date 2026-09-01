"""Test Executive Brief (modul MVP #14).

Yang diuji di sini bukan bentuk responsnya, melainkan tiga hal yang membuat brief layak
dibacakan kepada pimpinan:

1. **Angkanya sama dengan endpoint lain.** Brief merangkum sistem yang sama; bila jumlah
   peringatan aktif di brief berbeda dari `GET /warnings?status=ACTIVE`, salah satu dari
   keduanya berbohong dan tidak ada cara membedakan mana.
2. **Setiap angka turunan membawa dasarnya.** Angka tanpa asal-usul pada forum apel lebih
   berbahaya daripada tidak ada angka (CLAUDE.md §11, §26).
3. **Merangkum bukan pengecualian dari otorisasi.** Cakupan wilayah tetap menyempitkan
   angka, dan bagian yang permission-nya tidak dimiliki tidak ikut terangkum.
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
from prediksi_presisi_api.models import (
    CommanderDecision,
    Location,
    Permission,
    Recommendation,
    RiskScore,
    Role,
    RolePermission,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

BRIEF = "/api/v1/brief/daily"

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
    return _user_for(session, role, polsek)


def _user_for(session: Session, role: Role, polsek: str | None = None) -> User:
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


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _total(client: TestClient, headers: dict[str, str], path: str) -> int:
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    return int(response.json()["pagination"]["total_items"])


def test_brief_states_the_clock_it_was_written_against(
    client: TestClient, session: Session
) -> None:
    """Dokumen yang dibacakan harus menyebut kapan ia berlaku.

    Tanggal dan jam brief dihitung terhadap waktu acuan aplikasi (SDL-16), bukan jam
    dinding, dan penanda `demo_clock` ikut dibawa supaya pembaca tahu hal itu.
    """
    leader = _make_user(session, "Pimpinan")

    response = client.get(BRIEF, headers=_auth(client, leader))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reference_time"]
    assert body["brief_date"]
    assert body["brief_time"]
    assert body["window_hours"] == 24
    assert "demo_clock" in body
    assert body["clock_basis"]


def test_every_derived_number_carries_its_basis(client: TestClient, session: Session) -> None:
    # Tidak ada angka turunan yang tampil tanpa asal-usulnya (CLAUDE.md §11).
    leader = _make_user(session, "Pimpinan")

    body = client.get(BRIEF, headers=_auth(client, leader)).json()

    for key in (
        "scope_basis",
        "incidents_basis",
        "warnings_basis",
        "top_area_basis",
        "top_threats_basis",
        "pending_recommendations_basis",
        "pending_actions_basis",
        "accuracy_basis",
    ):
        assert body[key], f"{key} kosong"


def test_brief_numbers_match_the_endpoints_they_summarise(
    client: TestClient, session: Session
) -> None:
    """Brief tidak boleh menghitung versinya sendiri.

    Bila angka di sini menyimpang dari daftar aslinya, pembaca brief dan pembaca layar
    peringatan akan melihat sistem yang berbeda pada jam yang sama.
    """
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)

    body = client.get(BRIEF, headers=headers).json()

    assert body["active_warnings"] == _total(
        client, headers, "/api/v1/warnings?status=ACTIVE&page_size=1"
    )
    assert body["pending_recommendations"] == _total(
        client, headers, "/api/v1/recommendations?status=PENDING_REVIEW&page_size=1"
    )

    pending = client.get("/api/v1/operations/pending-decisions", headers=headers)
    assert body["pending_actions"] == len(pending.json()["data"])

    metrics = client.get("/api/v1/evaluation/metrics", headers=headers).json()
    assert body["accuracy"]["precision"] == metrics["precision"]
    assert body["accuracy"]["recall"] == metrics["recall"]


def test_jurisdiction_scope_narrows_the_brief(client: TestClient, session: Session) -> None:
    """Brief seorang Kapolsek tidak boleh memuat wilayah lain.

    Cakupan ditegakkan di backend, bukan dengan menyembunyikan bagian di layar
    (CLAUDE.md §15).
    """
    polsek = session.scalar(select(Location.polsek).where(Location.polsek.is_not(None)).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=str(polsek))
    leader = _make_user(session, "Pimpinan")

    scoped = client.get(BRIEF, headers=_auth(client, officer)).json()
    everything = client.get(BRIEF, headers=_auth(client, leader)).json()

    assert scoped["scope_polsek"] == polsek
    assert str(polsek) in scoped["scope_basis"]
    assert scoped["active_warnings"] < everything["active_warnings"]
    assert scoped["pending_recommendations"] < everything["pending_recommendations"]
    # Wilayah paling berisiko di brief Polsek harus berada di dalam wilayahnya sendiri.
    kecamatan_in_scope = set(
        session.scalars(
            select(Location.kecamatan).where(Location.polsek == polsek).distinct()
        ).all()
    )
    assert scoped["top_area"]["kecamatan"] in kecamatan_in_scope


def test_risk_class_is_read_from_the_column_not_recomputed(
    client: TestClient, session: Session
) -> None:
    """Kelas risiko dibaca apa adanya dari data.

    Ambang antar-kelas berstatus DEMO / PROPOSED (U-01); menghitung ulang kelas dari skor
    di lapisan API berarti mengunci angka yang belum disetujui siapa pun (CLAUDE.md §11).
    """
    leader = _make_user(session, "Pimpinan")

    body = client.get(BRIEF, headers=_auth(client, leader)).json()

    latest = session.scalar(
        select(RiskScore.assessment_date).order_by(RiskScore.assessment_date.desc())
    )
    peak = session.execute(
        select(RiskScore.risk_score, RiskScore.risk_class)
        .where(RiskScore.assessment_date == latest)
        .order_by(RiskScore.risk_score.desc())
        .limit(1)
    ).first()
    assert peak is not None

    assert body["assessment_date"] == str(latest)
    assert body["top_area"]["risk_score"] == peak.risk_score
    assert body["top_area"]["risk_class"] == peak.risk_class


def test_prominent_threats_carry_their_dangerous_hours(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")

    body = client.get(BRIEF, headers=_auth(client, leader)).json()

    assert body["top_threats"], "brief tanpa jenis ancaman tidak berguna bagi pimpinan"
    assert len({row["threat_type"] for row in body["top_threats"]}) == len(body["top_threats"])
    for row in body["top_threats"]:
        assert row["time_window"], row["threat_type"]
        assert row["risk_class"]


def test_accuracy_is_always_marked_proposed(client: TestClient, session: Session) -> None:
    # Aturan pencocokan prediksi vs kejadian nyata belum ditetapkan (U-03, CLAUDE.md §26).
    leader = _make_user(session, "Pimpinan")

    body = client.get(BRIEF, headers=_auth(client, leader)).json()

    assert body["accuracy"]["status"] == "PROPOSED"
    assert "U-03" in body["accuracy_basis"]


def test_a_decision_without_an_action_appears_in_the_queue(
    client: TestClient, session: Session
) -> None:
    """Keputusan yang sudah diambil tetapi belum dijalankan harus terlihat.

    Inilah keadaan yang sebelumnya tidak dapat dilihat dari mana pun: perintah turun,
    lapangan tidak bergerak.
    """
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)
    before = client.get(BRIEF, headers=headers).json()["pending_actions"]

    recommendation = session.scalar(
        select(Recommendation).where(Recommendation.status == "PENDING_REVIEW").limit(1)
    )
    assert recommendation is not None
    session.add(
        CommanderDecision(
            code=f"DEC-UJI-{uuid.uuid4().hex[:4]}",
            recommendation_id=recommendation.recommendation_id,
            decision_by=leader.user_id,
            decision="APPROVED",
            reason="Uji antrean tindakan.",
        )
    )
    session.flush()

    after = client.get(BRIEF, headers=headers).json()

    assert after["pending_actions"] == before + 1
    assert recommendation.code in {
        row["recommendation_code"] for row in after["pending_action_items"]
    }


def test_sections_without_permission_are_omitted_with_a_reason(
    client: TestClient, session: Session
) -> None:
    """Merangkum bukan pintu belakang.

    Role yang hanya memegang `dashboard:read` tetap boleh membuka brief, tetapi tidak
    menerima ringkasan data yang tidak boleh dibacanya. Bagian yang hilang menjelaskan
    dirinya, sehingga tidak dapat dikira sebagai data yang memang kosong.
    """
    role = Role(
        code=f"ROLE-UJI-{uuid.uuid4().hex[:4]}",
        role_name=f"Uji Dashboard {uuid.uuid4().hex[:4]}",
        level=6,
    )
    session.add(role)
    session.flush()
    dashboard_read = session.scalar(
        select(Permission).where(Permission.resource == "dashboard", Permission.action == "read")
    )
    assert dashboard_read is not None
    session.add(
        RolePermission(
            role_id=role.role_id, permission_id=dashboard_read.permission_id, scope="ALL"
        )
    )
    session.flush()
    user = _user_for(session, role)

    response = client.get(BRIEF, headers=_auth(client, user))

    assert response.status_code == 200, response.text
    body = response.json()
    for value, basis, permission in (
        ("incidents_recent", "incidents_basis", "crime:read"),
        ("active_warnings", "warnings_basis", "warning:read"),
        ("top_area", "top_area_basis", "risk_score:read"),
        ("pending_recommendations", "pending_recommendations_basis", "recommendation:read"),
        ("pending_actions", "pending_actions_basis", "operation:read"),
        ("accuracy", "accuracy_basis", "evaluation:read"),
    ):
        assert body[value] is None, value
        assert permission in body[basis], basis
