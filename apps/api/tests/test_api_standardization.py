"""Modul 1 mekanisme: penanda kendaraan, kelurahan tertunda, dugaan ganda, riwayat koreksi."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import visibility

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
    # Saringan ORM global (laporan ganda CONFIRMED tersembunyi) dipasang seperti di produksi.
    visibility.install()
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, session: Session, role_name: str) -> dict[str, str]:
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
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _kelurahan(session: Session) -> Location:
    row = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    )
    assert row is not None
    return row


def _kecamatan_location(session: Session, kecamatan: str) -> Location:
    row = session.scalar(
        select(Location).where(Location.kelurahan.is_(None), Location.kecamatan == kecamatan)
    )
    if row is None:
        row = Location(
            code=f"LOC-KEC-{uuid.uuid4().hex[:5]}",
            grid_id=f"kec:uji-{uuid.uuid4().hex[:5]}",
            polsek=f"Polsek {kecamatan}",
            kecamatan=kecamatan,
            kelurahan=None,
            grid_size_m=0,
            latitude=-6.2,
            longitude=106.8,
            geom="SRID=4326;POINT(106.8 -6.2)",
            location_type="KECAMATAN",
        )
        session.add(row)
        session.flush()
    return row


def _create(client: TestClient, headers: dict[str, str], body: dict[str, object]) -> dict[str, Any]:
    response = client.post("/api/v1/crimes", json=body, headers=headers)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def _area(
    client: TestClient, headers: dict[str, str], code: str, location: str, note: str = ""
) -> Response:
    body: dict[str, str] = {"location_code": location}
    if note:
        body["note"] = note
    response: Response = client.post(f"/api/v1/crimes/{code}/area", json=body, headers=headers)
    return response


def _entry(target: str, location_code: str, day: str = "2025-12-20") -> dict[str, object]:
    return {
        "incident_type": "CURANMOR",
        "incident_date": day,
        "incident_time": "22:30:00",
        "location_code": location_code,
        "location_type": "Parkiran",
        "modus": "Kunci T",
        "target_type": target,
    }


def test_officer_entry_sets_vehicle_flag_source_and_pending_area(
    client: TestClient, session: Session
) -> None:
    admin = _login(client, session, "Administrator")
    area = _kelurahan(session)
    created = client.post(
        "/api/v1/crimes", json=_entry("Kendaraan bermotor", area.code), headers=admin
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["vehicle_object"] is True and body["area_pending"] is False
    stored = session.scalar(select(CrimeIncident).where(CrimeIncident.code == body["code"]))
    assert stored is not None and stored.data_source is not None
    assert stored.data_source.startswith("ENTRI:")

    kec = _kecamatan_location(session, area.kecamatan)
    pending = client.post(
        "/api/v1/crimes", json=_entry("Uang", kec.code, "2025-11-02"), headers=admin
    ).json()
    assert pending["vehicle_object"] is False and pending["area_pending"] is True

    # Konfirmasi kelurahan: harus kelurahan di kecamatan yang sama; tercatat sebagai revisi.
    wrong = session.scalar(
        select(Location).where(
            Location.kelurahan.is_not(None), Location.kecamatan != area.kecamatan
        )
    )
    assert wrong is not None
    assert (
        client.post(
            f"/api/v1/crimes/{pending['code']}/area",
            json={"location_code": wrong.code},
            headers=admin,
        ).status_code
        == 400
    )
    fixed = client.post(
        f"/api/v1/crimes/{pending['code']}/area",
        json={"location_code": area.code, "note": "alamat dicek bersama Polsek"},
        headers=admin,
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["area_pending"] is False and fixed.json()["kelurahan"] == area.kelurahan
    history = client.get(f"/api/v1/crimes/{pending['code']}/revisions", headers=admin).json()[
        "data"
    ]
    assert [row["field"] for row in history] == ["location"]
    assert history[0]["note"] == "alamat dicek bersama Polsek"

    # Polsek tidak boleh membakukan (hanya Administrator, crime:triage).
    assert (
        client.post(
            f"/api/v1/crimes/{pending['code']}/area",
            json={"location_code": area.code},
            headers=_login(client, session, "Polsek"),
        ).status_code
        == 403
    )


def test_second_entry_same_place_same_day_is_flagged_and_confirmed_duplicate_disappears(
    client: TestClient, session: Session
) -> None:
    admin = _login(client, session, "Administrator")
    area = _kelurahan(session)
    first = client.post(
        "/api/v1/crimes", json=_entry("Kendaraan bermotor", area.code), headers=admin
    ).json()
    assert first["duplicate_status"] is None
    second = client.post(
        "/api/v1/crimes", json=_entry("Kendaraan bermotor", area.code), headers=admin
    ).json()
    assert second["duplicate_status"] == "SUSPECTED" and second["duplicate_of"] == first["code"]

    queue = client.get("/api/v1/crimes/standardization", headers=admin).json()
    assert second["code"] in [row["code"] for row in queue["suspected_duplicates"]["data"]]
    assert queue["suspected_duplicates"]["total"] >= 1 and "kelurahan_options" in queue

    confirmed = client.post(
        f"/api/v1/crimes/{second['code']}/duplicate",
        json={"status": "CONFIRMED", "note": "nomor LP sama"},
        headers=admin,
    )
    assert confirmed.status_code == 200 and confirmed.json()["duplicate_status"] == "CONFIRMED"
    # Yang dipastikan ganda hilang dari seluruh pembacaan ORM — termasuk daftar kejadian.
    codes = [
        row["code"]
        for row in client.get(
            "/api/v1/crimes?page_size=200&date_from=2025-12-20&date_to=2025-12-20", headers=admin
        ).json()["data"]
    ]
    assert first["code"] in codes and second["code"] not in codes
    assert (
        client.get(f"/api/v1/crimes/{second['code']}/revisions", headers=admin).status_code == 404
    )

    cleared = client.post(
        f"/api/v1/crimes/{first['code']}/duplicate",
        json={"status": "CLEARED", "note": "kejadian berbeda"},
        headers=admin,
    )
    assert cleared.status_code == 200 and cleared.json()["duplicate_status"] == "CLEARED"


def test_vehicle_filter_on_list(client: TestClient, session: Session) -> None:
    admin = _login(client, session, "Administrator")
    area = _kelurahan(session)
    client.post(
        "/api/v1/crimes", json=_entry("Kendaraan bermotor", area.code, "2025-10-05"), headers=admin
    )
    client.post(
        "/api/v1/crimes", json=_entry("Barang berharga", area.code, "2025-10-06"), headers=admin
    )
    rows = client.get(
        "/api/v1/crimes?vehicle_object=true&date_from=2025-10-05&date_to=2025-10-06&page_size=50",
        headers=admin,
    ).json()["data"]
    assert rows and all(row["vehicle_object"] for row in rows)
    assert date.fromisoformat(rows[0]["incident_date"]) >= date(2025, 10, 5)


# --- Mutu data (naskah Taskap 4.1; 18 November 2026) -------------------------------------


def _citizen_report(session: Session, area: Location, status: str, day: date) -> str:
    from datetime import datetime, time

    from prediksi_presisi_api.models import CitizenReport
    from prediksi_presisi_api.services import clock

    code = f"RPT-UJI-{uuid.uuid4().hex[:6]}"
    session.add(
        CitizenReport(
            code=code,
            reported_at=datetime.combine(day, time(9, 0), tzinfo=clock.JAKARTA),
            category="Pencurian Kendaraan",
            description="Motor hilang dari teras.",
            latitude=-6.2,
            longitude=106.8,
            geom="SRID=4326;POINT(106.8 -6.2)",
            location_id=area.location_id,
            status=status,
        )
    )
    session.flush()
    return code


def test_quality_summary_reports_completeness_flags_and_counting(
    client: TestClient, session: Session
) -> None:
    admin = _login(client, session, "Administrator")
    assert client.get("/api/v1/data-quality").status_code == 401
    assert (
        client.get("/api/v1/data-quality", headers=_login(client, session, "Fungsi")).status_code
        == 403
    )
    before = client.get("/api/v1/data-quality", headers=admin).json()
    area = _kelurahan(session)
    # Berlabel curanmor tetapi objeknya bukan kendaraan bermotor.
    odd = client.post(
        "/api/v1/crimes",
        json={**_entry("Barang berharga", area.code), "incident_date": "2025-12-30"},
        headers=admin,
    )
    assert odd.status_code == 201, odd.text
    after = client.get("/api/v1/data-quality", headers=admin).json()
    assert after["incidents"] == before["incidents"] + 1
    assert {row["field"] for row in after["completeness"]} == {
        "kelurahan",
        "jam",
        "koordinat",
        "objek_sasaran",
        "tempat_kejadian",
    }
    for row in after["completeness"]:
        assert 0 <= row["filled"] <= after["incidents"]

    def total(body: dict[str, Any], kind: str) -> int:
        return int(next(row["total"] for row in body["flags"] if row["kind"] == kind))

    assert total(after, "LABEL_OBJECT") == total(before, "LABEL_OBJECT") + 1
    listed = client.get(
        "/api/v1/data-quality/flags?kind=LABEL_OBJECT&limit=200", headers=admin
    ).json()
    assert odd.json()["code"] in [row["code"] for row in listed["data"]]
    assert listed["total"] == total(after, "LABEL_OBJECT")
    assert client.get("/api/v1/data-quality/flags?kind=ASAL", headers=admin).status_code == 400
    # Penandaan memakai aturan, dan itu dinyatakan — bukan disebut model.
    assert "aturan tertulis (bukan model)" in after["basis"]


def test_citizen_report_is_matched_to_an_incident_only_by_decision_with_reason(
    client: TestClient, session: Session
) -> None:
    admin = _login(client, session, "Administrator")
    area = _kelurahan(session)
    day = date(2025, 12, 29)
    incident = client.post(
        "/api/v1/crimes",
        json={**_entry("Kendaraan bermotor", area.code), "incident_date": day.isoformat()},
        headers=admin,
    ).json()
    waiting = _citizen_report(session, area, "RECEIVED", day)
    verified = _citizen_report(session, area, "VERIFIED", date(2025, 12, 30))
    extra = _citizen_report(session, area, "VERIFIED", date(2025, 12, 30))
    base = client.get("/api/v1/data-quality", headers=admin).json()["counting"]

    queue = client.get("/api/v1/data-quality/matches?limit=100", headers=admin).json()
    codes = [row["code"] for row in queue["data"]]
    # Yang belum diverifikasi berstatus menunggu pemeriksaan: tidak diusulkan, tidak dihitung.
    assert verified in codes and waiting not in codes
    row = next(item for item in queue["data"] if item["code"] == verified)
    proposed = next(c for c in row["candidates"] if c["code"] == incident["code"])
    assert proposed["days_apart"] == 1 and proposed["same_kelurahan"] is True

    path = f"/api/v1/citizen-reports/{verified}/match"
    body = {"decision": "MATCHED", "incident_code": incident["code"], "reason": "plat sama"}
    assert client.post(path, json={**body, "reason": ""}, headers=admin).status_code == 400
    assert client.post(path, json={**body, "incident_code": None}, headers=admin).status_code == 400
    assert (
        client.post(path, json=body, headers=_login(client, session, "Polsek")).status_code == 403
    )
    assert (
        client.post(
            f"/api/v1/citizen-reports/{waiting}/match", json=body, headers=admin
        ).status_code
        == 409
    )
    matched = client.post(path, json=body, headers=admin)
    assert matched.status_code == 200, matched.text
    assert matched.json()["matched_incident"] == incident["code"]
    assert matched.json()["match_reason"] == "plat sama"
    lone = client.post(
        f"/api/v1/citizen-reports/{extra}/match",
        json={"decision": "NOT_MATCHED", "reason": "tidak ada laporan polisi"},
        headers=admin,
    )
    assert lone.status_code == 200 and lone.json()["matched_incident"] is None

    counting = client.get("/api/v1/data-quality", headers=admin).json()["counting"]
    # Yang ditautkan tidak menambah hitungan kejadian resmi — satu peristiwa terhitung sekali;
    # yang terverifikasi tanpa padanan resmi menjadi kejadian tambahan, dihitung terpisah.
    assert counting["official"] == base["official"]
    assert counting["linked_reports"] == base["linked_reports"] + 1
    assert counting["additional_verified"] == base["additional_verified"] + 1
    assert counting["awaiting_match"] == base["awaiting_match"] - 2
    assert counting["awaiting_verification"] == base["awaiting_verification"]
    after = client.get("/api/v1/data-quality/matches?limit=100", headers=admin).json()
    assert verified not in [item["code"] for item in after["data"]]


def test_duplicate_decision_requires_a_reason(client: TestClient, session: Session) -> None:
    admin = _login(client, session, "Administrator")
    area = _kelurahan(session)
    body = {**_entry("Kendaraan bermotor", area.code), "incident_date": "2017-04-04"}
    client.post("/api/v1/crimes", json=body, headers=admin)
    second = client.post("/api/v1/crimes", json=body, headers=admin).json()
    assert second["duplicate_status"] == "SUSPECTED"
    path = f"/api/v1/crimes/{second['code']}/duplicate"
    assert client.post(path, json={"status": "CLEARED"}, headers=admin).status_code == 400
    assert (
        client.post(
            path, json={"status": "CLEARED", "note": "TKP berbeda"}, headers=admin
        ).status_code
        == 200
    )
