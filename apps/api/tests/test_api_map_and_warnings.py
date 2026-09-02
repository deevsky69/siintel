"""Test endpoint peta dan transisi status peringatan dini (TASK 082–084, 111).

Yang diuji di sini bukan sekadar bentuk respons, melainkan empat hal yang mudah rusak
tanpa disadari:

1. **Agregasi benar** — skor kecamatan pada peta memang skor tertinggi sel di dalamnya,
   dibandingkan terhadap hasil query langsung ke database, bukan terhadap angka yang
   kebetulan keluar dari API.
2. **Cakupan ditegakkan backend** — pengguna Polsek hanya melihat wilayahnya, dan
   kecamatan di luar cakupan dijawab 404, bukan 403 (docs/05 §1).
3. **Pelaku transisi tercatat** — acknowledge/resolve mengisi `*_by` dan `*_at`, tidak
   hanya mengubah kolom status.
4. **Transisi ganda ditolak 409** dan tetap meninggalkan jejak audit.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    AuditLog,
    CrimeIncident,
    EarlyWarning,
    Location,
    Permission,
    RiskScore,
    Role,
    RolePermission,
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


def _make_user(session: Session, role_name: str, polsek: str | None = None) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None
    return _user_for_role(session, role, polsek)


def _user_for_role(session: Session, role: Role, polsek: str | None = None) -> User:
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


def _role_granting(session: Session, permissions: list[str]) -> Role:
    """Role uji dengan tepat permission yang disebutkan — untuk menguji gerbang kedua."""
    role = Role(
        code=f"ROLE-UJI-{uuid.uuid4().hex[:4]}", role_name=f"Uji {uuid.uuid4().hex[:4]}", level=6
    )
    session.add(role)
    session.flush()

    for name in permissions:
        resource, _, action = name.partition(":")
        permission = session.scalar(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        assert permission is not None, name
        session.add(
            RolePermission(
                role_id=role.role_id, permission_id=permission.permission_id, scope="ALL"
            )
        )
    session.flush()
    return role


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _a_warning(session: Session, status: str) -> tuple[EarlyWarning, Location]:
    row = session.execute(
        select(EarlyWarning, Location)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .where(EarlyWarning.status == status)
        .order_by(EarlyWarning.code)
        .limit(1)
    ).first()
    assert row is not None, f"data dummy tidak memuat peringatan berstatus {status}"
    return row[0], row[1]


# --- Peta: agregasi ---------------------------------------------------------------------


def test_current_risk_matches_the_database(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/map/current-risk", headers=_auth(client, leader))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["areas"], "layer risiko berjalan tidak boleh kosong pada data dummy"
    assert body["assessment_date"]

    # Skor kecamatan harus benar-benar skor tertinggi sel di dalamnya.
    expected: dict[str, int] = {
        kecamatan: int(score)
        for kecamatan, score in session.execute(
            select(Location.kecamatan, func.max(RiskScore.risk_score))
            .join(Location, Location.location_id == RiskScore.location_id)
            .where(RiskScore.assessment_date == date.fromisoformat(body["assessment_date"]))
            .group_by(Location.kecamatan)
        ).all()
    }
    assert {area["kecamatan"]: area["risk_score"] for area in body["areas"]} == expected

    first = body["areas"][0]
    assert first["risk_class"], "kelas risiko diambil dari sel puncak, tidak boleh kosong"
    assert first["cell_count"] > 0
    assert first["threats"]
    assert max(threat["risk_score"] for threat in first["threats"]) == first["risk_score"]
    # Urutan menurun supaya peta dapat menampilkan yang terparah lebih dahulu.
    assert [area["risk_score"] for area in body["areas"]] == sorted(
        (area["risk_score"] for area in body["areas"]), reverse=True
    )


def test_derived_numbers_state_where_they_come_from(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/map/current-risk", headers=_auth(client, leader))

    # Angka turunan tidak boleh tampil tanpa penjelasan asalnya (pola dashboard.py).
    assert "agregasi" in response.json()["aggregation_basis"]
    assert "DEMO / PROPOSED" in response.json()["aggregation_basis"]


def test_current_risk_is_limited_to_the_officers_jurisdiction(
    client: TestClient, session: Session
) -> None:
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    response = client.get("/api/v1/map/current-risk", headers=_auth(client, officer))

    assert response.status_code == 200
    areas = response.json()["areas"]
    assert areas
    assert {area["polsek"] for area in areas} == {polsek}


def test_current_risk_needs_the_risk_score_permission_too(
    client: TestClient, session: Session
) -> None:
    # `map:read` saja tidak cukup: layer ini membaca risk_scores (docs/05 §2.4).
    role = _role_granting(session, ["map:read"])
    user = _user_for_role(session, role)

    response = client.get("/api/v1/map/current-risk", headers=_auth(client, user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    denied = session.scalars(
        select(AuditLog).where(
            AuditLog.user_id == user.user_id,
            AuditLog.result == "DENIED",
            AuditLog.resource_type == "risk_score",
        )
    ).all()
    assert denied, "penolakan permission kedua harus ikut tercatat di audit"


# --- Peta: layer prediktif --------------------------------------------------------------


def test_predictive_heatmap_only_returns_the_requested_horizon(
    client: TestClient, session: Session
) -> None:
    analyst = _make_user(session, "Administrator")

    response = client.get(
        "/api/v1/map/predictive-heatmap?horizon=6H", headers=_auth(client, analyst)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["horizon"] == "6H"
    assert body["areas"]
    for area in body["areas"]:
        assert area["risk_score"] >= max(t["risk_score"] for t in area["threats"])
        # Prediksi tidak menyimpan kelas risiko; API tidak boleh mengarangnya.
        assert "risk_class" not in area


def test_predictive_heatmap_rejects_an_unknown_horizon(
    client: TestClient, session: Session
) -> None:
    analyst = _make_user(session, "Administrator")

    response = client.get(
        "/api/v1/map/predictive-heatmap?horizon=99H", headers=_auth(client, analyst)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# --- Peta: panel detail kecamatan -------------------------------------------------------


def test_area_detail_answers_what_where_when_risk_confidence_why(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")
    kecamatan = session.scalar(select(Location.kecamatan).limit(1))
    assert kecamatan is not None

    response = client.get(f"/api/v1/map/area/{kecamatan}", headers=_auth(client, leader))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kecamatan"] == kecamatan
    assert body["grid_count"] > 0
    assert body["threats"], "panel klik harus menyebut potensi ancaman"
    assert body["critical_time_window"], "jendela paling rawan harus ada"
    assert body["history"]["total_incidents"] > 0
    assert body["history"]["date_from"] and body["history"]["date_to"]

    assert body["top_predictions"], "panel klik harus membawa prediksi teratas"
    for prediction in body["top_predictions"]:
        assert prediction["threat_type"]  # WHAT
        assert prediction["kecamatan"] == kecamatan  # WHERE
        assert prediction["window_start"] and prediction["window_end"]  # WHEN
        assert prediction["risk_score"] is not None  # RISK
        assert prediction["confidence"] is not None  # CONFIDENCE
        assert prediction["dominant_factors"]  # WHY
        assert all(
            factor["source"] in {"RULE", "MODEL"} for factor in prediction["dominant_factors"]
        )
        assert prediction["status"] != "DRAFT"


def test_area_detail_only_counts_warnings_that_are_still_active(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")
    warning, location = _a_warning(session, "ACTIVE")

    response = client.get(f"/api/v1/map/area/{location.kecamatan}", headers=_auth(client, leader))

    assert response.status_code == 200
    active = response.json()["active_warnings"]
    assert {row["status"] for row in active} == {"ACTIVE"}
    assert warning.code in {row["code"] for row in active}


def test_area_outside_the_jurisdiction_is_answered_404_not_403(
    client: TestClient, session: Session
) -> None:
    # 403 akan membocorkan bahwa kecamatan itu memang ada di wilayah lain (docs/05 §1).
    own, other = session.execute(
        select(Location.polsek, Location.kecamatan).distinct().order_by(Location.polsek).limit(2)
    ).all()
    officer = _make_user(session, "Polsek", polsek=own[0])

    response = client.get(f"/api/v1/map/area/{other[1]}", headers=_auth(client, officer))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_unknown_area_is_not_found(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/map/area/Kecamatan Tidak Ada", headers=_auth(client, leader))

    assert response.status_code == 404


# --- Transisi status peringatan ---------------------------------------------------------


def test_acknowledge_records_who_received_the_warning(client: TestClient, session: Session) -> None:
    operator = _make_user(session, "Administrator")
    warning, _location = _a_warning(session, "ACTIVE")

    response = client.post(
        f"/api/v1/warnings/{warning.code}/acknowledge", headers=_auth(client, operator)
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACKNOWLEDGED"
    assert response.json()["acknowledged_at"]

    session.expire(warning)
    assert warning.status == "ACKNOWLEDGED"
    # CHECK `acknowledged_needs_actor`: waktu tidak pernah terisi tanpa pelakunya.
    assert warning.acknowledged_by == operator.user_id
    assert warning.acknowledged_at is not None

    recorded = session.scalars(
        select(AuditLog).where(
            AuditLog.action == "ACK_WARNING",
            AuditLog.resource_id == warning.code,
            AuditLog.user_id == operator.user_id,
            AuditLog.result == "SUCCESS",
        )
    ).all()
    assert recorded, "acknowledge wajib meninggalkan audit ACK_WARNING"
    assert recorded[0].detail == {"status_before": "ACTIVE", "status_after": "ACKNOWLEDGED"}


def test_acknowledging_twice_is_a_conflict(client: TestClient, session: Session) -> None:
    operator = _make_user(session, "Administrator")
    warning, _location = _a_warning(session, "ACTIVE")
    headers = _auth(client, operator)

    first = client.post(f"/api/v1/warnings/{warning.code}/acknowledge", headers=headers)
    assert first.status_code == 200, first.text

    second = client.post(f"/api/v1/warnings/{warning.code}/acknowledge", headers=headers)

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"

    # Pelaku pertama tidak boleh tertimpa oleh percobaan kedua.
    session.expire(warning)
    assert warning.acknowledged_by == operator.user_id


def test_resolve_records_the_actor(client: TestClient, session: Session) -> None:
    operator = _make_user(session, "Administrator")
    warning, _location = _a_warning(session, "ACKNOWLEDGED")

    response = client.post(
        f"/api/v1/warnings/{warning.code}/resolve", headers=_auth(client, operator)
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RESOLVED"

    session.expire(warning)
    assert warning.status == "RESOLVED"
    assert warning.resolved_by == operator.user_id
    assert warning.resolved_at is not None

    assert session.scalars(
        select(AuditLog).where(
            AuditLog.action == "RESOLVE_WARNING",
            AuditLog.resource_id == warning.code,
            AuditLog.result == "SUCCESS",
        )
    ).all(), "resolve wajib meninggalkan audit RESOLVE_WARNING"


def test_resolving_a_resolved_warning_is_a_conflict(client: TestClient, session: Session) -> None:
    operator = _make_user(session, "Administrator")
    warning, _location = _a_warning(session, "RESOLVED")

    response = client.post(
        f"/api/v1/warnings/{warning.code}/resolve", headers=_auth(client, operator)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"

    # Transisi yang ditolak pun harus terlihat pada audit.
    assert session.scalars(
        select(AuditLog).where(
            AuditLog.action == "RESOLVE_WARNING",
            AuditLog.resource_id == warning.code,
            AuditLog.user_id == operator.user_id,
            AuditLog.result == "FAILED",
        )
    ).all()


def test_officer_cannot_acknowledge_a_warning_from_another_polsek(
    client: TestClient, session: Session
) -> None:
    warning, location = _a_warning(session, "ACTIVE")
    other_polsek = session.scalar(
        select(Location.polsek).where(Location.polsek != location.polsek).limit(1)
    )
    assert other_polsek is not None
    officer = _make_user(session, "Polsek", polsek=other_polsek)

    response = client.post(
        f"/api/v1/warnings/{warning.code}/acknowledge", headers=_auth(client, officer)
    )

    assert response.status_code == 404
    session.expire(warning)
    assert warning.status == "ACTIVE"


def test_officer_may_acknowledge_inside_its_own_jurisdiction(
    client: TestClient, session: Session
) -> None:
    warning, location = _a_warning(session, "ACTIVE")
    officer = _make_user(session, "Polsek", polsek=location.polsek)

    response = client.post(
        f"/api/v1/warnings/{warning.code}/acknowledge", headers=_auth(client, officer)
    )

    assert response.status_code == 200, response.text
    session.expire(warning)
    assert warning.acknowledged_by == officer.user_id


def test_resolve_requires_its_own_permission(client: TestClient, session: Session) -> None:
    # Role Polsek memiliki warning:acknowledge tetapi tidak warning:resolve
    # (config/rbac/permissions.yaml — pemberian ini masih PROPOSED).
    warning, location = _a_warning(session, "ACTIVE")
    officer = _make_user(session, "Polsek", polsek=location.polsek)

    response = client.post(
        f"/api/v1/warnings/{warning.code}/resolve", headers=_auth(client, officer)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_map_carries_the_weights_version_that_produced_the_scores(
    client: TestClient, session: Session
) -> None:
    """Ketertelusuran bobot (CLAUDE.md §25).

    Skor risiko dihitung dengan bobot dari `config/risk/`, yang masih berstatus
    `DEMO / PROPOSED`. Tanpa versinya ikut keluar, angka di layar tidak dapat
    dikembalikan ke konfigurasi yang menghasilkannya — dan pertanyaan "bobotnya dari
    mana" tidak dapat dijawab saat paparan.
    """
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)

    expected = session.scalar(
        select(RiskScore.weights_version).where(RiskScore.weights_version.is_not(None)).limit(1)
    )
    assert expected is not None, "data awal tidak memuat weights_version"

    listed = client.get("/api/v1/map/current-risk", headers=headers)
    assert listed.status_code == 200, listed.text
    areas = listed.json()["areas"]
    assert areas, "tidak ada wilayah yang dapat diperiksa"
    assert all(area["weights_version"] == expected for area in areas)

    detail = client.get(
        f"/api/v1/map/area/{areas[0]['kecamatan']}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["weights_version"] == expected


# --- Peta: layer historis ---------------------------------------------------------------


def _historical(client: TestClient, user: User, months: int = 12) -> dict[str, object]:
    response = client.get(f"/api/v1/map/historical?months={months}", headers=_auth(client, user))
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_historical_counts_match_the_database(client: TestClient, session: Session) -> None:
    """Cacah per kecamatan dibandingkan terhadap query langsung, bukan terhadap dirinya sendiri.

    Jendela diambil dari respons, bukan ditulis ulang di sini: waktu acuan aplikasi dapat
    berubah, dan test yang mengunci tanggalnya akan gagal karena alasan yang salah.
    """
    leader = _make_user(session, "Pimpinan")
    body = _historical(client, leader, months=36)

    expected = dict(
        session.execute(
            select(Location.kecamatan, func.count())
            .select_from(CrimeIncident)
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(
                CrimeIncident.incident_date >= date.fromisoformat(str(body["window_from"])),
                CrimeIncident.incident_date <= date.fromisoformat(str(body["window_to"])),
            )
            .group_by(Location.kecamatan)
        ).all()
    )

    # Tanpa penegasan ini perbandingan di bawah lulus ketika keduanya kosong — dan
    # endpoint yang tidak mengembalikan apa pun akan terbaca sebagai endpoint yang benar.
    assert expected, "data dummy tidak memuat kejadian pada jendela 36 bulan"

    areas = {area["kecamatan"]: area["incidents"] for area in body["areas"]}  # type: ignore[index,union-attr]
    assert areas == {name: int(count) for name, count in expected.items()}
    assert body["total_incidents"] == sum(expected.values())


def test_historical_window_excludes_what_falls_outside_it(
    client: TestClient, session: Session
) -> None:
    """Jendela yang lebih pendek tidak boleh membawa kejadian di luarnya.

    Tanpa penjagaan ini, `months` dapat berhenti berpengaruh tanpa ada yang terlihat rusak:
    layar tetap menampilkan angka, hanya saja angka yang salah.
    """
    leader = _make_user(session, "Pimpinan")

    wide = _historical(client, leader, months=36)
    narrow = _historical(client, leader, months=1)

    assert date.fromisoformat(str(narrow["window_from"])) > date.fromisoformat(
        str(wide["window_from"])
    )
    assert int(narrow["total_incidents"]) <= int(wide["total_incidents"])  # type: ignore[arg-type]

    observed_from = narrow["observed_from"]
    if observed_from is not None:
        assert date.fromisoformat(str(observed_from)) >= date.fromisoformat(
            str(narrow["window_from"])
        )


def test_historical_points_carry_coordinates_and_add_up(
    client: TestClient, session: Session
) -> None:
    """Titik peta harus dapat digambar **dan** menjumlah ke cacah wilayah.

    Titik yang tidak menjumlah berarti ada kejadian yang hilang dari peta tanpa jejak.
    """
    leader = _make_user(session, "Pimpinan")
    body = _historical(client, leader, months=36)

    points = body["points"]
    assert isinstance(points, list) and points

    for point in points:
        assert isinstance(point["latitude"], float)
        assert isinstance(point["longitude"], float)
        assert point["incidents"] >= 1
        assert point["location_code"]

    assert sum(int(point["incidents"]) for point in points) == int(body["total_incidents"])  # type: ignore[arg-type]


def test_historical_never_reports_a_risk_class(client: TestClient, session: Session) -> None:
    """Layer ini mencacah kejadian, bukan menilai risiko — dan tidak boleh terbaca sebaliknya.

    `risk_class` di sini akan menjadi ambang kedua di luar `config/risk/`, persis yang
    dilarang CLAUDE.md §12; ia juga akan menyatakan wilayah dengan kejadian terbanyak
    sebagai wilayah paling rawan, yang tidak dapat disimpulkan dari cacah mentah.
    """
    leader = _make_user(session, "Pimpinan")
    body = _historical(client, leader, months=36)

    assert "risk_class" not in json.dumps(body)
    assert "risk_score" not in json.dumps(body)
    assert "cacah kejadian mentah" in str(body["aggregation_basis"])


def test_historical_rejects_a_window_length_it_does_not_offer(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/map/historical?months=7", headers=_auth(client, leader))

    assert response.status_code == 400, response.text
    assert "months" in response.text


def test_historical_is_limited_to_the_users_jurisdiction(
    client: TestClient, session: Session
) -> None:
    """Pengguna Polsek tidak boleh menyimpulkan sebaran kejadian di wilayah lain.

    Diperiksa pada `areas` **dan** `points`: membatasi satu tetapi tidak yang lain adalah
    kebocoran yang tidak terlihat di layar karena keduanya digambar berlapis.
    """
    scoped_polsek = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None)).order_by(Location.polsek)
    )
    assert scoped_polsek is not None

    officer = _make_user(session, "Polsek", polsek=scoped_polsek)
    body = _historical(client, officer, months=36)

    assert body["areas"], "pengguna Polsek harus tetap melihat wilayahnya sendiri"
    assert {area["polsek"] for area in body["areas"]} == {scoped_polsek}  # type: ignore[index,union-attr]

    allowed = set(
        session.scalars(
            select(Location.kecamatan).where(Location.polsek == scoped_polsek).distinct()
        ).all()
    )
    assert {point["kecamatan"] for point in body["points"]} <= allowed  # type: ignore[index,union-attr]


def test_historical_requires_both_gates(client: TestClient, session: Session) -> None:
    """`map:read` saja tidak cukup: layer ini membuka data kejadian, jadi `crime:read` wajib."""
    role = _role_granting(session, ["map:read"])
    user = _user_for_role(session, role)

    response = client.get("/api/v1/map/historical", headers=_auth(client, user))

    assert response.status_code == 403, response.text
