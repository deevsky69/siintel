"""Test lengan umpan balik: tindakan operasional dan hasil nyata (TASK 131).

Yang dijaga di sini adalah mata rantai yang membuat evaluasi punya arti — tanpa catatan
bahwa keputusan benar-benar dijalankan dan apa hasilnya, precision dan recall hanya
membandingkan prediksi dengan dirinya sendiri.

Invarian terpentingnya tidak dijaga oleh kode ini melainkan oleh trigger database sejak
migration 0006; test di sini memastikan lapisan API tidak membuka jalan memutarinya.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    AuditLog,
    CommanderDecision,
    OperationalAction,
    PoliceUnit,
    Recommendation,
    Role,
    User,
)
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


def _make_user(
    session: Session, role_name: str, polsek: str | None = None, function: str | None = None
) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, f"role {role_name} belum ada — jalankan seed"

    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        polsek=polsek,
        function=function,
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


def _decision_without_action(session: Session, decision: str) -> CommanderDecision:
    """Membuat keputusan yang belum ditindaklanjuti, alih-alih mencarinya di data awal.

    Versi sebelumnya mencari baris yang kebetulan tersedia — dan patah begitu keputusan
    terakhir yang menganggur dipakai orang lain. Test yang bergantung pada isi basis data
    akan gagal karena sistem dipakai, bukan karena perilakunya berubah.

    Barisnya dibuat di dalam transaksi yang dibatalkan setelah test, sehingga tidak
    menghabiskan apa pun.
    """
    recommendation = session.scalar(
        select(Recommendation)
        .outerjoin(
            CommanderDecision,
            CommanderDecision.recommendation_id == Recommendation.recommendation_id,
        )
        .where(CommanderDecision.decision_id.is_(None))
        .limit(1)
    )
    assert recommendation is not None, "data awal tidak menyediakan rekomendasi tanpa keputusan"

    decider = session.scalar(select(User).limit(1))
    assert decider is not None

    record = CommanderDecision(
        code=f"DEC-UJI-{uuid.uuid4().hex[:6]}",
        recommendation_id=recommendation.recommendation_id,
        decision_by=decider.user_id,
        decision=decision,
        modified_text="Disesuaikan untuk pengujian." if decision == "MODIFIED" else None,
    )
    session.add(record)
    session.flush()
    return record


def _unit(session: Session) -> PoliceUnit:
    unit = session.scalar(select(PoliceUnit).limit(1))
    assert unit is not None
    return unit


def test_action_can_be_recorded_from_an_approving_decision(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Administrator")
    decision = _decision_without_action(session, "APPROVED")

    response = client.post(
        "/api/v1/operations",
        json={"decision_code": decision.code, "unit_code": _unit(session).code},
        headers=_auth(client, officer),
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "PLANNED"


def test_action_cannot_be_recorded_from_a_rejected_decision(
    client: TestClient, session: Session
) -> None:
    """Aturan yang sama dijaga trigger database; API tidak boleh membuka jalan memutar."""
    officer = _make_user(session, "Administrator")
    rejected = session.scalar(
        select(CommanderDecision).where(CommanderDecision.decision == "REJECTED").limit(1)
    )
    assert rejected is not None

    response = client.post(
        "/api/v1/operations",
        json={"decision_code": rejected.code, "unit_code": _unit(session).code},
        headers=_auth(client, officer),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_one_decision_produces_at_most_one_action(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Administrator")
    decision = _decision_without_action(session, "APPROVED")
    headers = _auth(client, officer)
    payload = {"decision_code": decision.code, "unit_code": _unit(session).code}

    assert client.post("/api/v1/operations", json=payload, headers=headers).status_code == 201
    second = client.post("/api/v1/operations", json=payload, headers=headers)

    assert second.status_code == 409


def test_leader_cannot_record_actions(client: TestClient, session: Session) -> None:
    """Yang memutuskan bukan yang melaksanakan — dan penolakannya meninggalkan jejak."""
    leader = _make_user(session, "Pimpinan")
    decision = _decision_without_action(session, "APPROVED")

    response = client.post(
        "/api/v1/operations",
        json={"decision_code": decision.code, "unit_code": _unit(session).code},
        headers=_auth(client, leader),
    )

    assert response.status_code == 403
    denial = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == leader.user_id)
        .where(AuditLog.result == "DENIED")
    )
    assert denial is not None


def test_result_is_refused_when_it_would_have_no_duration(
    client: TestClient, session: Session
) -> None:
    """Penugasan berdurasi nol ditolak, dan alasannya dapat ditindaklanjuti.

    Constraint `ck_operational_actions_time_order` menjaga hal yang sama di database.
    Tanpa pemeriksaan di lapisan API, pelanggarannya muncul sebagai 500 tanpa penjelasan.

    Keadaan ini bukan teoretis: jam acuan aplikasi beku saat demo (SDL-16), sehingga
    penugasan yang dibuat dan diselesaikan pada sesi yang sama memiliki waktu mulai dan
    selesai yang sama persis. Yang benar adalah **menanyakan** waktu selesainya, bukan
    mengarang durasi agar constraint-nya lolos.

    Waktu di sini disebut eksplisit, tidak mengandalkan jam acuan sedang beku — test
    yang bergantung pada keadaan lingkungan akan lulus atau gagal karena alasan lain.
    """
    officer = _make_user(session, "Administrator")
    decision = _decision_without_action(session, "APPROVED")
    headers = _auth(client, officer)
    created = client.post(
        "/api/v1/operations",
        json={"decision_code": decision.code, "unit_code": _unit(session).code},
        headers=headers,
    )
    code = created.json()["code"]
    started = created.json()["start_at"]

    response = client.post(
        f"/api/v1/operations/{code}/result",
        json={"status": "COMPLETED", "result": "Selesai.", "end_at": started},
        headers=headers,
    )

    assert response.status_code == 422
    message = response.json()["error"]["message"]
    assert "waktu selesai" in message.lower()
    # Pesan disajikan dalam WIB, sama seperti seluruh antarmuka. Menyebut UTC membuat
    # petugas yang baru mengetik pukul 10.00 membaca 03.00 dan mengira sistemnya keliru.
    assert "WIB" in message
    assert "UTC" not in message

    session.expire_all()
    stored = session.scalar(select(OperationalAction).where(OperationalAction.code == code))
    assert stored is not None
    assert stored.status == "PLANNED", "percobaan yang ditolak tidak boleh mengubah status"


def test_result_closes_the_loop(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Administrator")
    decision = _decision_without_action(session, "APPROVED")
    headers = _auth(client, officer)
    created = client.post(
        "/api/v1/operations",
        json={"decision_code": decision.code, "unit_code": _unit(session).code},
        headers=headers,
    )
    code = created.json()["code"]
    started = created.json()["start_at"]

    end_at = (datetime.fromisoformat(started) + timedelta(hours=6)).isoformat()
    response = client.post(
        f"/api/v1/operations/{code}/result",
        json={
            "status": "COMPLETED",
            "result": "Patroli dilaksanakan, nihil kejadian.",
            "end_at": end_at,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "COMPLETED"

    session.expire_all()
    stored = session.scalar(select(OperationalAction).where(OperationalAction.code == code))
    assert stored is not None
    assert stored.result == "Patroli dilaksanakan, nihil kejadian."
    assert stored.end_at is not None and stored.end_at > stored.start_at

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "RECORD_OPERATION_RESULT")
        .where(AuditLog.resource_id == code)
    )
    assert entry is not None


def test_a_finished_action_cannot_be_rewritten(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Administrator")
    decision = _decision_without_action(session, "APPROVED")
    headers = _auth(client, officer)
    code = client.post(
        "/api/v1/operations",
        json={"decision_code": decision.code, "unit_code": _unit(session).code},
        headers=headers,
    ).json()["code"]

    started = session.scalar(
        select(OperationalAction.start_at).where(OperationalAction.code == code)
    )
    assert started is not None
    end_at = (started + timedelta(hours=2)).isoformat()

    first = {"status": "COMPLETED", "result": "Selesai.", "end_at": end_at}
    assert (
        client.post(f"/api/v1/operations/{code}/result", json=first, headers=headers).status_code
        == 200
    )

    second = client.post(
        f"/api/v1/operations/{code}/result",
        json={"status": "CANCELLED", "result": "Diubah.", "end_at": end_at},
        headers=headers,
    )

    assert second.status_code == 409
    failed = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "RECORD_OPERATION_RESULT")
        .where(AuditLog.resource_id == code)
        .where(AuditLog.result == "FAILED")
    )
    assert failed is not None, "penolakan transisi harus ikut tercatat, bukan hanya keberhasilan"


def test_pending_decisions_only_lists_undone_approvals(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Administrator")

    response = client.get("/api/v1/operations/pending-decisions", headers=_auth(client, officer))

    assert response.status_code == 200
    rows = response.json()["data"]
    assert all(row["decision"] in {"APPROVED", "MODIFIED"} for row in rows)

    done = {
        code
        for code in session.scalars(
            select(CommanderDecision.code).join(
                OperationalAction,
                OperationalAction.decision_id == CommanderDecision.decision_id,
            )
        ).all()
    }
    assert not ({row["decision_code"] for row in rows} & done)


def test_operations_are_scoped_by_jurisdiction(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Polsek", polsek="Polsek Tebet")
    centre = _make_user(session, "Administrator")

    scoped = client.get("/api/v1/operations?page_size=1", headers=_auth(client, officer))
    full = client.get("/api/v1/operations?page_size=1", headers=_auth(client, centre))

    assert scoped.status_code == 200
    assert scoped.json()["pagination"]["total_items"] < full.json()["pagination"]["total_items"], (
        "Polsek menerima seluruh tindakan operasional Jakarta Selatan"
    )


def test_operations_are_scoped_by_function(client: TestClient, session: Session) -> None:
    """Cakupan fungsi ditegakkan lewat `police_units.function`.

    Inilah endpoint pertama yang membuktikan deklarasi `OWN_FUNCTION` pada peran Fungsi
    benar-benar dapat ditegakkan — sebelumnya deklarasi itu ada tanpa penegakan.
    """
    unit_function = session.scalar(
        select(PoliceUnit.function).where(PoliceUnit.function.is_not(None))
    )
    assert unit_function is not None
    officer = _make_user(session, "Fungsi", function=str(unit_function))
    centre = _make_user(session, "Administrator")

    scoped = client.get("/api/v1/operations?page_size=1", headers=_auth(client, officer))
    full = client.get("/api/v1/operations?page_size=1", headers=_auth(client, centre))

    assert scoped.status_code == 200
    assert scoped.json()["pagination"]["total_items"] < full.json()["pagination"]["total_items"]
