"""Berkas perkara 3C: lacak laporan (LP + PIN), cek kendaraan, layar petugas, data dummy."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers import public_cases
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, CaseFile, Location, Role, User
from prediksi_presisi_api.models.case_file import hash_pin, normalize_plate
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.seeding.case_files_dummy import seed_dummy_case_files

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
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
    public_cases.limiter.reset()
    public_cases.pin_failures.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    public_cases.limiter.reset()
    public_cases.pin_failures.reset()


def _login(
    client: TestClient, session: Session, role_name: str, polsek: str | None = None
) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        status="ACTIVE",
        must_change_password=False,
        polsek=polsek,
    )
    session.add(user)
    session.flush()
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_helpers_normalise_and_hash() -> None:
    assert normalize_plate(" b 1234 abc ") == "B1234ABC"
    assert hash_pin("LP/B/1", "0001") != hash_pin("LP/B/2", "0001")
    assert hash_pin(" lp/b/1 ", "0001") == hash_pin("LP/B/1", "0001")


def test_dummy_seed_is_deterministic_labelled_and_idempotent(session: Session) -> None:
    first = seed_dummy_case_files(session, reference=date(2026, 1, 1))
    assert len(first) == 48 and first[0].pin.isdigit()
    again = seed_dummy_case_files(session, reference=date(2026, 1, 1))
    assert [row.lp_number for row in again] == [row.lp_number for row in first]
    rows = session.scalars(select(CaseFile).where(CaseFile.is_dummy.is_(True))).all()
    assert len(rows) == 48
    assert all(
        row.dummy_pin and row.reporter_pin_hash == hash_pin(row.lp_number, row.dummy_pin)
        for row in rows
    )
    assert any(row.vehicle_plate for row in rows)


def test_tracking_needs_lp_and_pin_and_answers_uniformly(
    client: TestClient, session: Session
) -> None:
    made = seed_dummy_case_files(session, reference=date(2026, 1, 1))
    sample = made[0]
    ok = client.get(
        "/api/v1/public/cases/track", params={"lp": sample.lp_number, "pin": sample.pin}
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["lp_number"] == sample.lp_number and body["is_dummy"] is True
    assert body["stage"] == sample.stage and body["history"][0]["stage"] == "DITERIMA"
    for forbidden in ("reporter", "nama", "pin_hash", "dummy_pin"):
        assert forbidden not in ok.text

    wrong_pin = client.get(
        "/api/v1/public/cases/track",
        params={"lp": sample.lp_number, "pin": "0000" if sample.pin != "0000" else "0001"},
    )
    missing = client.get(
        "/api/v1/public/cases/track", params={"lp": "LP/B/999999/XII/2099/SPKT", "pin": "1234"}
    )
    assert wrong_pin.status_code == 404 and missing.status_code == 404
    assert wrong_pin.json()["error"]["message"] == missing.json()["error"]["message"]

    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "TRACK_CASE", AuditLog.resource_id == sample.lp_number
        )
    )
    assert entry is not None and entry.user_id is None


def test_vehicle_check_reveals_only_whether_a_report_exists(
    client: TestClient, session: Session
) -> None:
    made = seed_dummy_case_files(session, reference=date(2026, 1, 1))
    with_plate = next(row for row in made if row.plate)
    found = client.get("/api/v1/public/vehicles/check", params={"plat": with_plate.plate.lower()})
    assert found.status_code == 200 and found.json()["found"] is True
    record = found.json()["records"][0]
    assert set(record) == {"crime_type", "reported_month", "kecamatan", "recovered", "is_dummy"}
    assert "LP/" not in found.text

    none = client.get("/api/v1/public/vehicles/check", params={"plat": "B 0000 ZZZ"})
    assert none.status_code == 200 and none.json()["found"] is False
    assert client.get("/api/v1/public/vehicles/check", params={"plat": "B1"}).status_code == 400

    for _ in range(8):
        client.get("/api/v1/public/vehicles/check", params={"plat": "B 0000 ZZZ"})
    assert (
        client.get("/api/v1/public/vehicles/check", params={"plat": "B 0000 ZZZ"}).status_code
        == 429
    )


def test_officers_manage_case_files_within_their_jurisdiction(
    client: TestClient, session: Session
) -> None:
    area = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    )
    assert area is not None
    other = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None), Location.polsek != area.polsek)
    )
    assert other is not None

    assert client.get("/api/v1/case-files").status_code == 401
    assert (
        client.get("/api/v1/case-files", headers=_login(client, session, "Fungsi")).status_code
        == 403
    )

    polsek = _login(client, session, "Polsek", polsek=area.polsek)
    payload = {
        "lp_number": f"LP/B/UJI-{uuid.uuid4().hex[:4]}/XI/2026/SPKT/POLSEK {area.polsek.upper()}",
        "crime_type": "CURANMOR",
        "kecamatan": area.kecamatan,
        "kelurahan": area.kelurahan,
        "reported_on": "2026-11-01",
        "vehicle_plate": "b 7777 uji",
        "vehicle_desc": "Honda Beat uji",
    }
    created = client.post("/api/v1/case-files", json=payload, headers=polsek)
    assert created.status_code == 201, created.text
    pin = created.json()["reporter_pin"]
    assert len(pin) == 4 and created.json()["dummy_pin"] is None  # PIN nyata hanya sekali

    # Pelapor dapat melacaknya dengan PIN itu; daftar petugas tidak membocorkan PIN.
    assert (
        client.get(
            "/api/v1/public/cases/track", params={"lp": payload["lp_number"], "pin": pin}
        ).status_code
        == 200
    )
    listing = client.get("/api/v1/case-files", headers=polsek).json()
    mine = next(row for row in listing["data"] if row["lp_number"] == payload["lp_number"].upper())
    assert mine["dummy_pin"] is None and "reporter_pin" not in mine

    # Di luar wilayah: Polsek lain tidak melihat dan tidak dapat memindahkan tahapnya.
    outsider = _login(client, session, "Polsek", polsek=other.polsek)
    assert (
        client.post(
            f"/api/v1/case-files/{payload['lp_number']}/stage",
            json={"stage": "LIDIK"},
            headers=outsider,
        ).status_code
        == 404
    )

    moved = client.post(
        f"/api/v1/case-files/{payload['lp_number']}/stage",
        json={"stage": "LIDIK", "note": "Pemeriksaan saksi."},
        headers=polsek,
    )
    assert moved.status_code == 200 and moved.json()["stage"] == "LIDIK"
    assert moved.json()["history"][-1]["note"] == "Pemeriksaan saksi."
    assert (
        client.post(
            f"/api/v1/case-files/{payload['lp_number']}/stage",
            json={"stage": "LIDIK"},
            headers=polsek,
        ).status_code
        == 409
    )
    tracked = client.get(
        "/api/v1/public/cases/track", params={"lp": payload["lp_number"], "pin": pin}
    ).json()
    assert tracked["stage_label"] == "Penyelidikan" and tracked["is_dummy"] is False

    # Pimpinan membaca seluruh Polres; Administrator juga.
    assert (
        client.get("/api/v1/case-files", headers=_login(client, session, "Pimpinan")).status_code
        == 200
    )


def test_pin_guessing_is_locked_per_lp_regardless_of_address(
    client: TestClient, session: Session
) -> None:
    """Pembatas per alamat dapat dilewati dengan memalsukan header; kunci per nomor LP tidak."""
    made = seed_dummy_case_files(session, reference=date(2026, 1, 1))
    sample = made[1]
    wrong = "0000" if sample.pin != "0000" else "0001"
    for index in range(5):
        response = client.get(
            "/api/v1/public/cases/track",
            params={"lp": sample.lp_number, "pin": wrong},
            headers={"X-Forwarded-For": f"203.0.113.{index}"},  # alamat berganti-ganti
        )
        assert response.status_code == 404
    locked = client.get(
        "/api/v1/public/cases/track",
        params={"lp": sample.lp_number, "pin": sample.pin},  # bahkan PIN yang benar
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert locked.status_code == 429
