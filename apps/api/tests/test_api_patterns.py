"""Test Crime Pattern DNA (TASK 094).

Yang diuji di sini **bukan** bahwa respons konsisten dengan dirinya sendiri, melainkan
bahwa setiap angka sama dengan hasil agregasi yang dihitung **langsung ke database**
lewat SQL yang ditulis terpisah dari kode endpoint. Membandingkan respons dengan respons
hanya membuktikan endpoint konsisten dalam kesalahannya.

Selain itu diuji tiga hal yang mengikat menurut CLAUDE.md:

- cakupan wilayah benar-benar ditegakkan (§15) — pengguna Polsek menerima angka lebih kecil;
- tidak ada bahasa prediksi/skor/keyakinan yang menyelinap ke respons (§27);
- persentase tidak pernah dikirim tanpa penyebutnya (§11).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
ENDPOINT = "/api/v1/analytics/crime-pattern-dna"

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


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _distribution(profile: dict[str, Any], dimension: str, dimension_id: str) -> dict[str, Any]:
    """Satu distribusi dari profil, dicari menurut id — bukan menurut urutan."""
    found = next(row for row in profile[dimension] if row["id"] == dimension_id)
    assert isinstance(found, dict)
    return found


def _counts(session: Session, sql: str, **params: object) -> dict[str, int]:
    """Agregasi pembanding, ditulis sebagai SQL lepas — bukan lewat kode endpoint."""
    return {str(key): int(value) for key, value in session.execute(text(sql), params).all()}


# ----------------------------------------------------------------------------
# Daftar jenis
# ----------------------------------------------------------------------------


def test_threat_types_match_the_database(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    response = client.get(ENDPOINT, headers=_auth(client, analyst))

    assert response.status_code == 200, response.text
    body = response.json()
    listed = {row["threat_type"]: row["incidents"] for row in body["threat_types"]}
    assert listed == _counts(
        session, "select incident_type, count(*) from crime_incidents group by 1"
    )
    # Tanpa jenis yang diminta, profil tidak dikirim — layar pemilih tidak membutuhkannya.
    assert body["profile"] is None
    assert body["threat_type"] is None


def test_source_carries_the_range_that_produced_the_numbers(
    client: TestClient, session: Session
) -> None:
    analyst = _make_user(session, "Analyst")

    body = client.get(ENDPOINT, headers=_auth(client, analyst)).json()

    date_from, date_to, total = session.execute(
        text("select min(incident_date), max(incident_date), count(*) from crime_incidents")
    ).one()
    assert body["source"]["date_from"] == date_from.isoformat()
    assert body["source"]["date_to"] == date_to.isoformat()
    assert body["source"]["incidents"] == total
    assert body["source"]["table"] == "crime_incidents"


# ----------------------------------------------------------------------------
# Lima dimensi, dibandingkan langsung ke database
# ----------------------------------------------------------------------------


def test_where_dimension_matches_direct_sql(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    profile = client.get(f"{ENDPOINT}?threat_type=CURANMOR", headers=_auth(client, analyst)).json()[
        "profile"
    ]

    kecamatan = _distribution(profile, "where", "kecamatan")
    assert {row["key"]: row["incidents"] for row in kecamatan["buckets"]} == _counts(
        session,
        """
        select l.kecamatan, count(*)
        from crime_incidents ci join locations l on l.location_id = ci.location_id
        where ci.incident_type = :jenis group by 1
        """,
        jenis="CURANMOR",
    )

    tkp = _distribution(profile, "where", "location_type")
    assert {row["key"]: row["incidents"] for row in tkp["buckets"]} == _counts(
        session,
        """
        select location_type, count(*)
        from crime_incidents where incident_type = :jenis group by 1
        """,
        jenis="CURANMOR",
    )

    # Distribusi kategori diurutkan menurun; peringkat adalah bagian dari kontrak.
    counts = [row["incidents"] for row in kecamatan["buckets"]]
    assert counts == sorted(counts, reverse=True)


def test_when_dimension_matches_direct_sql(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    profile = client.get(f"{ENDPOINT}?threat_type=CURANMOR", headers=_auth(client, analyst)).json()[
        "profile"
    ]

    hours = _distribution(profile, "when", "hour")
    # Ke-24 jam selalu dikirim, termasuk yang kosong: jam bernilai nol memang nol.
    assert [row["key"] for row in hours["buckets"]] == [str(index) for index in range(24)]
    from_db = _counts(
        session,
        """
        select extract(hour from incident_time)::int, count(*)
        from crime_incidents where incident_type = :jenis group by 1
        """,
        jenis="CURANMOR",
    )
    assert {row["key"]: row["incidents"] for row in hours["buckets"] if row["incidents"]} == from_db

    days = _distribution(profile, "when", "day_of_week")
    assert [row["label"] for row in days["buckets"]] == [
        "Senin",
        "Selasa",
        "Rabu",
        "Kamis",
        "Jumat",
        "Sabtu",
        "Minggu",
    ]
    assert {row["key"]: row["incidents"] for row in days["buckets"] if row["incidents"]} == _counts(
        session,
        """
        select extract(isodow from incident_date)::int, count(*)
        from crime_incidents where incident_type = :jenis group by 1
        """,
        jenis="CURANMOR",
    )


def test_when_dimension_uses_local_time_not_utc(client: TestClient, session: Session) -> None:
    """Jam rawan dihitung dari `incident_time` (WIB), bukan dari `occurred_at` (UTC).

    Keduanya berbeda tujuh jam pada dataset ini; memakai kolom yang salah menggeser
    seluruh profil WHEN tanpa satu pun angka terlihat janggal.
    """
    analyst = _make_user(session, "Analyst")

    profile = client.get(f"{ENDPOINT}?threat_type=CURANMOR", headers=_auth(client, analyst)).json()[
        "profile"
    ]
    hours = _distribution(profile, "when", "hour")
    busiest = max(hours["buckets"], key=lambda row: row["incidents"])["key"]

    local_peak, utc_peak = session.execute(
        text(
            """
            select
              (select extract(hour from incident_time)::int from crime_incidents
                where incident_type = :jenis group by 1 order by count(*) desc limit 1),
              (select extract(hour from occurred_at)::int from crime_incidents
                where incident_type = :jenis group by 1 order by count(*) desc limit 1)
            """
        ),
        {"jenis": "CURANMOR"},
    ).one()

    assert int(busiest) == local_peak
    assert local_peak != utc_peak, "dataset tidak lagi membedakan WIB dan UTC — uji ini tumpul"


def test_how_and_target_dimensions_match_direct_sql(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    profile = client.get(f"{ENDPOINT}?threat_type=CURAS", headers=_auth(client, analyst)).json()[
        "profile"
    ]

    modus = _distribution(profile, "how", "modus")
    assert {row["key"]: row["incidents"] for row in modus["buckets"]} == _counts(
        session,
        "select modus, count(*) from crime_incidents where incident_type = :jenis group by 1",
        jenis="CURAS",
    )

    target = _distribution(profile, "target", "target_type")
    assert {row["key"]: row["incidents"] for row in target["buckets"]} == _counts(
        session,
        "select target_type, count(*) from crime_incidents where incident_type = :jenis group by 1",
        jenis="CURAS",
    )


def test_repeat_grids_match_direct_sql(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    profile = client.get(f"{ENDPOINT}?threat_type=TAWURAN", headers=_auth(client, analyst)).json()[
        "profile"
    ]
    repeat = profile["repeat"]

    rows = session.execute(
        text(
            """
            select l.grid_id, count(*) n, min(ci.incident_date), max(ci.incident_date)
            from crime_incidents ci join locations l on l.location_id = ci.location_id
            where ci.incident_type = :jenis
            group by 1 having count(*) > 1
            """
        ),
        {"jenis": "TAWURAN"},
    ).all()
    expected = {grid: (total, first, last) for grid, total, first, last in rows}

    assert {row["grid_id"] for row in repeat["grids"]} == set(expected)
    assert repeat["repeat_grids"] == len(expected)
    for row in repeat["grids"]:
        total, first, last = expected[row["grid_id"]]
        assert row["incidents"] == total
        assert row["first_date"] == first.isoformat()
        assert row["last_date"] == last.isoformat()
        # Rentang tanggal membedakan "delapan kejadian sepekan" dari "delapan kejadian tiga tahun".
        assert row["span_days"] == (last - first).days

    all_grids, single = session.execute(
        text(
            """
            select count(*), count(*) filter (where n = 1) from (
              select ci.location_id, count(*) n from crime_incidents ci
              where ci.incident_type = :jenis group by 1
            ) t
            """
        ),
        {"jenis": "TAWURAN"},
    ).one()
    assert repeat["grids_with_incidents"] == all_grids
    assert repeat["single_incident_grids"] == single


# ----------------------------------------------------------------------------
# Persentase, penyebut, dan batas penafsiran
# ----------------------------------------------------------------------------


def test_every_distribution_carries_its_denominator(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    profile = client.get(f"{ENDPOINT}?threat_type=CURANMOR", headers=_auth(client, analyst)).json()[
        "profile"
    ]

    for dimension in ("where", "when", "how", "target"):
        for distribution in profile[dimension]:
            assert distribution["denominator"] == profile["incidents"]
            for bucket in distribution["buckets"]:
                # Persentase tanpa penyebutnya menyesatkan (CLAUDE.md §11).
                expected = round(100 * bucket["incidents"] / profile["incidents"], 1)
                assert bucket["share_percent"] == expected

    assert profile["repeat"]["denominator"] == profile["incidents"]


def test_sample_size_is_stated_in_terms_of_its_own_arithmetic(
    client: TestClient, session: Session
) -> None:
    """Ketelitian sampel dinyatakan tanpa mengarang ambang "terlalu sedikit"."""
    analyst = _make_user(session, "Analyst")

    body = client.get(f"{ENDPOINT}?threat_type=TAWURAN", headers=_auth(client, analyst)).json()
    profile = body["profile"]

    assert str(profile["incidents"]) in profile["sample_note"]
    assert "persen poin" in profile["sample_note"]


def test_response_never_speaks_as_a_prediction(client: TestClient, session: Session) -> None:
    """Analisis deskriptif tidak boleh membawa skor risiko atau tingkat keyakinan.

    Bukan sekadar kerapian kata: begitu frekuensi historis diberi `confidence`, hitungan
    masa lalu terbaca sebagai pernyataan tentang masa depan (CLAUDE.md §27).
    """
    analyst = _make_user(session, "Analyst")

    response = client.get(f"{ENDPOINT}?threat_type=CURANMOR", headers=_auth(client, analyst))

    body = response.json()
    serialized = response.text
    for forbidden in ("risk_score", "confidence", "forecast_horizon", "model_version"):
        assert forbidden not in serialized, (
            f"'{forbidden}' tidak boleh ada pada analisis deskriptif"
        )

    assert "bukan prediksi" in body["analysis_basis"].lower()
    assert "near-repeat" in body["profile"]["repeat"]["basis"]


# ----------------------------------------------------------------------------
# Otorisasi dan cakupan wilayah
# ----------------------------------------------------------------------------


def test_endpoint_requires_analytics_read(client: TestClient, session: Session) -> None:
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

    response = client.get(ENDPOINT, headers=_auth(client, user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_unauthenticated_request_is_refused(client: TestClient) -> None:
    assert client.get(ENDPOINT).status_code == 401


def test_jurisdiction_scope_is_enforced_in_the_query(client: TestClient, session: Session) -> None:
    """Pengguna Polsek hanya menerima kejadian wilayahnya — sampai ke tingkat grid."""
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    body = client.get(f"{ENDPOINT}?threat_type=CURANMOR", headers=_auth(client, officer)).json()
    profile = body["profile"]

    scoped_total = session.execute(
        text(
            """
            select count(*) from crime_incidents ci
            join locations l on l.location_id = ci.location_id
            where ci.incident_type = :jenis and l.polsek = :polsek
            """
        ),
        {"jenis": "CURANMOR", "polsek": polsek},
    ).scalar_one()

    assert profile["incidents"] == scoped_total
    assert scoped_total < 464, "cakupan tidak menyempitkan apa pun — uji ini tumpul"

    kecamatan = _distribution(profile, "where", "kecamatan")
    assert {row["key"] for row in kecamatan["buckets"]} == set(
        session.scalars(
            select(Location.kecamatan).where(Location.polsek == polsek).distinct()
        ).all()
    )

    allowed_grids = set(
        session.scalars(select(Location.grid_id).where(Location.polsek == polsek)).all()
    )
    assert {row["grid_id"] for row in profile["repeat"]["grids"]} <= allowed_grids
    assert body["source"]["scope"] == polsek
    assert polsek in body["scope_basis"]


def test_scoped_user_without_a_jurisdiction_is_refused(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Polsek", polsek=None)

    assert client.get(ENDPOINT, headers=_auth(client, officer)).status_code == 403


# ----------------------------------------------------------------------------
# Validasi masukan
# ----------------------------------------------------------------------------


def test_unknown_threat_type_is_rejected_with_the_available_list(
    client: TestClient, session: Session
) -> None:
    analyst = _make_user(session, "Analyst")

    response = client.get(f"{ENDPOINT}?threat_type=TIDAK_ADA", headers=_auth(client, analyst))

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "CURANMOR" in body["error"]["details"][0]["issue"]


def test_threat_type_is_matched_case_insensitively(client: TestClient, session: Session) -> None:
    analyst = _make_user(session, "Analyst")

    response = client.get(f"{ENDPOINT}?threat_type=curanmor", headers=_auth(client, analyst))

    assert response.status_code == 200
    assert response.json()["threat_type"] == "CURANMOR"
