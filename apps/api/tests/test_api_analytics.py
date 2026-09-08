"""Test Crime Analytics dan daftar laporan intelijen (TASK 033, 035).

Seperti pada `test_api_patterns.py`, yang diuji **bukan** bahwa respons konsisten dengan
dirinya sendiri melainkan bahwa setiap angka sama dengan agregasi yang dihitung langsung
ke database lewat SQL yang ditulis terpisah dari kode endpoint. Membandingkan respons
dengan respons hanya membuktikan endpoint konsisten dalam kesalahannya.

Selain kebenaran angka, empat hal yang mengikat menurut CLAUDE.md ikut dijaga:

- cakupan wilayah ditegakkan di query (§15) — pengguna Polsek menerima angka lebih kecil;
- kewenangan diperiksa di backend (§21) — termasuk peran Fungsi yang **tidak** memegang
  `intelligence:read`, sehingga daftar laporan intelijen harus 403 baginya;
- tidak ada bahasa prediksi/skor/keyakinan yang menyelinap ke analisis deskriptif (§27);
- persentase tidak pernah dikirim tanpa penyebutnya, dan angka turunan membawa `*_basis`
  (§11).
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

INTELLIGENCE = "/api/v1/intelligence-reports"
TREND = "/api/v1/analytics/trend"
TIME_PATTERN = "/api/v1/analytics/time-pattern"
SPATIAL = "/api/v1/analytics/spatial-pattern"

ANALYTICS_ENDPOINTS = (TREND, TIME_PATTERN, SPATIAL)

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


def _counts(session: Session, sql: str, **params: object) -> dict[str, int]:
    """Agregasi pembanding, ditulis sebagai SQL lepas — bukan lewat kode endpoint."""
    return {str(key): int(value) for key, value in session.execute(text(sql), params).all()}


def _get(client: TestClient, session: Session, path: str, role: str = "Administrator") -> Any:
    response = client.get(path, headers=_auth(client, _make_user(session, role)))
    assert response.status_code == 200, response.text
    return response.json()


# ----------------------------------------------------------------------------
# Laporan intelijen — daftar, penyaring, cakupan
# ----------------------------------------------------------------------------


def test_intelligence_list_matches_the_database(client: TestClient, session: Session) -> None:
    body = _get(client, session, f"{INTELLIGENCE}?page_size=200")

    total = session.execute(text("select count(*) from intelligence_reports")).scalar_one()
    assert body["pagination"]["total_items"] == total
    assert len(body["data"]) == min(total, 200)
    assert body["source"]["reports_in_scope"] == total

    codes = {row["code"] for row in body["data"]}
    assert (
        codes
        == {
            str(code)
            for code in session.execute(
                text("select code from intelligence_reports limit 200")
            ).scalars()
        }
        or len(codes) == 200
    )


def test_intelligence_rows_carry_the_assessment_fields(
    client: TestClient, session: Session
) -> None:
    """Kolom penilaian ikut dikirim; tanpanya layar hanya menjadi daftar judul."""
    body = _get(client, session, f"{INTELLIGENCE}?page_size=1")
    row = body["data"][0]

    expected = session.execute(
        text(
            """
            select r.report_date, r.category, r.reliability, r.confidence, r.urgency,
                   r.impact, r.status, l.kecamatan, l.polsek, l.grid_id
            from intelligence_reports r join locations l on l.location_id = r.location_id
            where r.code = :code
            """
        ),
        {"code": row["code"]},
    ).one()

    assert row["report_date"] == expected[0].isoformat()
    assert (
        row["category"],
        row["reliability"],
        row["confidence"],
        row["urgency"],
        row["impact"],
        row["status"],
        row["kecamatan"],
        row["polsek"],
        row["grid_id"],
    ) == tuple(expected[1:])


def test_intelligence_is_sorted_newest_first_and_paginates_without_repeating(
    client: TestClient, session: Session
) -> None:
    """Urutan harus tetap: halaman kedua tidak boleh memuat baris halaman pertama."""
    user = _make_user(session, "Administrator")
    headers = _auth(client, user)

    first = client.get(f"{INTELLIGENCE}?page=1&page_size=10", headers=headers).json()
    second = client.get(f"{INTELLIGENCE}?page=2&page_size=10", headers=headers).json()

    dates = [row["report_date"] for row in first["data"]]
    assert dates == sorted(dates, reverse=True)
    assert first["data"][-1]["report_date"] >= second["data"][0]["report_date"]
    assert {row["code"] for row in first["data"]}.isdisjoint(
        {row["code"] for row in second["data"]}
    )


def test_intelligence_filters_match_direct_sql(client: TestClient, session: Session) -> None:
    user = _make_user(session, "Administrator")
    headers = _auth(client, user)

    by_status = _counts(session, "select status, count(*) from intelligence_reports group by 1")
    body = client.get(f"{INTELLIGENCE}?status=verified&page_size=200", headers=headers).json()

    assert body["pagination"]["total_items"] == by_status["VERIFIED"]
    assert {row["status"] for row in body["data"]} == {"VERIFIED"}

    by_category = _counts(session, "select category, count(*) from intelligence_reports group by 1")
    category = max(by_category, key=lambda name: by_category[name])
    filtered = client.get(
        f"{INTELLIGENCE}?category={category.replace(' ', '%20')}&page_size=200", headers=headers
    ).json()
    assert filtered["pagination"]["total_items"] == by_category[category]


def test_intelligence_facets_count_the_whole_scope_not_the_filtered_page(
    client: TestClient, session: Session
) -> None:
    """Penyaring menyebut berapa yang akan muncul bila pilihannya diganti.

    Karena itu jumlahnya dihitung atas seluruh cakupan, bukan atas hasil penyaringan yang
    sedang tampil — dan responsnya menyatakan hal itu lewat `filter_basis`.
    """
    body = _get(client, session, f"{INTELLIGENCE}?status=NEW&page_size=5")

    assert {row["value"]: row["reports"] for row in body["filters"]["status"]} == _counts(
        session,
        "select status, count(*) from intelligence_reports where status is not null group by 1",
    )
    assert {row["value"]: row["reports"] for row in body["filters"]["category"]} == _counts(
        session,
        "select category, count(*) from intelligence_reports where category is not null group by 1",
    )
    assert "SELURUH laporan" in body["filter_basis"]


def test_intelligence_scope_is_enforced_in_the_query(client: TestClient, session: Session) -> None:
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    body = client.get(f"{INTELLIGENCE}?page_size=200", headers=_auth(client, officer)).json()

    scoped = session.execute(
        text(
            """
            select count(*) from intelligence_reports r
            join locations l on l.location_id = r.location_id
            where l.polsek = :polsek
            """
        ),
        {"polsek": polsek},
    ).scalar_one()
    total = session.execute(text("select count(*) from intelligence_reports")).scalar_one()

    assert body["pagination"]["total_items"] == scoped
    assert scoped < total, "cakupan tidak menyempitkan apa pun — uji ini tumpul"
    assert {row["polsek"] for row in body["data"]} == {polsek}
    assert body["source"]["scope"] == polsek
    # Penyaring pun tidak boleh membocorkan nilai yang hanya ada di wilayah lain.
    assert sum(row["reports"] for row in body["filters"]["status"]) <= scoped


def test_intelligence_requires_intelligence_read(client: TestClient, session: Session) -> None:
    """Peran Fungsi tidak memegang `intelligence:read` — itu keadaan RBAC yang berlaku.

    Pencabutannya disengaja: `intelligence_reports` tidak punya kolom fungsi, sehingga
    cakupan `OWN_FUNCTION` mustahil ditegakkan, dan menaikkannya menjadi `ALL` adalah
    pelebaran kewenangan yang menunggu keputusan pemilik proyek
    (`config/rbac/permissions.yaml`). Uji ini menjaga agar endpoint baru tidak diam-diam
    membatalkan keputusan itu.
    """
    officer = _make_user(session, "Fungsi")

    response = client.get(INTELLIGENCE, headers=_auth(client, officer))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_intelligence_denial_is_recorded_in_the_audit_trail(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Fungsi")
    before = session.execute(
        text("select count(*) from audit_logs where result = 'DENIED'")
    ).scalar_one()

    client.get(INTELLIGENCE, headers=_auth(client, officer))

    after = session.execute(
        text("select count(*) from audit_logs where result = 'DENIED'")
    ).scalar_one()
    assert after == before + 1


def test_intelligence_unauthenticated_request_is_refused(client: TestClient) -> None:
    assert client.get(INTELLIGENCE).status_code == 401


def test_intelligence_states_that_its_scores_are_recorded_not_computed(
    client: TestClient, session: Session
) -> None:
    """`confidence` di sini bukan keyakinan model — dan responsnya harus mengatakannya."""
    body = _get(client, session, f"{INTELLIGENCE}?page_size=1")

    assert "bukan keluaran model" in body["assessment_basis"]


# ----------------------------------------------------------------------------
# Tren per bulan
# ----------------------------------------------------------------------------


def test_trend_series_match_direct_sql(client: TestClient, session: Session) -> None:
    body = _get(client, session, TREND)

    assert {row["threat_type"]: row["incidents"] for row in body["series"]} == _counts(
        session, "select incident_type, count(*) from crime_incidents group by 1"
    )

    monthly = _counts(
        session,
        "select to_char(incident_date, 'YYYY-MM'), count(*) from crime_incidents group by 1",
    )
    assert {row["key"]: row["incidents"] for row in body["months"] if row["incidents"]} == monthly
    assert body["incidents"] == sum(monthly.values())

    # Deret terbesar lebih dulu; peringkat adalah bagian dari kontrak.
    counts = [row["incidents"] for row in body["series"]]
    assert counts == sorted(counts, reverse=True)


def test_trend_axis_keeps_months_without_incidents(client: TestClient, session: Session) -> None:
    """Bulan kosong tetap nol pada sumbu — membuangnya akan merapatkan grafik."""
    body = _get(client, session, f"{TREND}?date_from=2023-01-01&date_to=2025-12-31")

    assert body["months_counted"] == 36
    assert [row["key"] for row in body["months"]][:2] == ["2023-01", "2023-02"]
    for row in body["series"]:
        assert len(row["monthly"]) == 36


def test_trend_respects_the_requested_range_and_threat_type(
    client: TestClient, session: Session
) -> None:
    body = _get(
        client, session, f"{TREND}?threat_type=curanmor&date_from=2025-01-01&date_to=2025-06-30"
    )

    assert body["threat_type"] == "CURANMOR"
    assert {row["key"]: row["incidents"] for row in body["months"] if row["incidents"]} == _counts(
        session,
        """
        select to_char(incident_date, 'YYYY-MM'), count(*) from crime_incidents
        where incident_type = 'CURANMOR' and incident_date between :awal and :akhir
        group by 1
        """,
        awal="2025-01-01",
        akhir="2025-06-30",
    )
    assert body["months_counted"] == 6


def test_trend_derived_numbers_carry_their_basis(client: TestClient, session: Session) -> None:
    """Rata-rata dan bulan terbanyak tidak pernah tampil tanpa penyebut/dasarnya."""
    body = _get(client, session, TREND)

    assert body["mean_per_month"] == round(body["incidents"] / body["months_counted"], 1)
    assert str(body["months_counted"]) in body["mean_basis"]
    assert "bukan" in body["peak_basis"].lower()

    peak = max(row["incidents"] for row in body["months"])
    assert body["peak_month"]["incidents"] == peak
    for row in body["months"]:
        assert row["share_percent"] == round(100 * row["incidents"] / body["denominator"], 1)


def test_trend_scope_is_enforced_in_the_query(client: TestClient, session: Session) -> None:
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    body = client.get(TREND, headers=_auth(client, officer)).json()

    scoped = session.execute(
        text(
            """
            select count(*) from crime_incidents ci
            join locations l on l.location_id = ci.location_id where l.polsek = :polsek
            """
        ),
        {"polsek": polsek},
    ).scalar_one()
    total = session.execute(text("select count(*) from crime_incidents")).scalar_one()

    assert body["incidents"] == scoped
    assert scoped < total, "cakupan tidak menyempitkan apa pun — uji ini tumpul"
    assert body["source"]["scope"] == polsek
    assert polsek in body["scope_basis"]


# ----------------------------------------------------------------------------
# Matriks hari x jam
# ----------------------------------------------------------------------------


def test_time_pattern_matrix_matches_direct_sql(client: TestClient, session: Session) -> None:
    body = _get(client, session, TIME_PATTERN)

    cells = {
        f"{row['day']}-{cell['hour']}": cell["incidents"]
        for row in body["days"]
        for cell in row["cells"]
        if cell["incidents"]
    }
    assert cells == _counts(
        session,
        """
        select extract(isodow from incident_date)::int || '-' ||
               extract(hour from incident_time)::int, count(*)
        from crime_incidents group by 1
        """,
    )
    assert body["cells"] == 7 * 24
    assert (
        sum(cell["incidents"] for row in body["days"] for cell in row["cells"]) == body["incidents"]
    )


def test_time_pattern_marginals_match_direct_sql(client: TestClient, session: Session) -> None:
    """Total per hari dan per jam harus sama dengan agregasi satu dimensi."""
    body = _get(client, session, TIME_PATTERN)

    assert {str(row["day"]): row["incidents"] for row in body["days"]} == _counts(
        session,
        "select extract(isodow from incident_date)::int, count(*) from crime_incidents group by 1",
    )
    assert {
        str(row["hour"]): row["incidents"] for row in body["hours"] if row["incidents"]
    } == _counts(
        session,
        "select extract(hour from incident_time)::int, count(*) from crime_incidents group by 1",
    )
    assert [row["label"] for row in body["days"]] == [
        "Senin",
        "Selasa",
        "Rabu",
        "Kamis",
        "Jumat",
        "Sabtu",
        "Minggu",
    ]


def test_time_pattern_uses_local_time_not_utc(client: TestClient, session: Session) -> None:
    """Jam rawan dihitung dari `incident_time` (WIB), bukan `occurred_at` (UTC)."""
    body = _get(client, session, TIME_PATTERN)

    busiest = max(body["hours"], key=lambda row: row["incidents"])["hour"]

    # Jam tersibuk dibandingkan sebagai HIMPUNAN, bukan satu nilai.
    #
    # Dua jam dapat memiliki cacah kejadian yang sama persis — dan sejak Pesanggrahan
    # ditambahkan, jam 18 dan 21 memang seri. "Jam tersibuk" karena itu tidak bermakna
    # tunggal, sementara `max()` di Python dan `order by ... limit 1` di SQL memutus seri
    # dengan cara yang berbeda. Membandingkan satu nilai membuat uji ini gagal karena
    # aritmetika pemutus seri, bukan karena yang hendak dibuktikannya.
    #
    # Yang dibuktikan tetap sama: jam dihitung dari `incident_time` (WIB), bukan
    # `occurred_at` (UTC).
    local_peaks, utc_peaks = session.execute(
        text(
            """
            select
              (select array_agg(hour order by hour) from (
                 select extract(hour from incident_time)::int as hour, count(*) as total
                 from crime_incidents group by 1
                 having count(*) = (select max(total) from (
                   select count(*) as total from crime_incidents
                   group by extract(hour from incident_time)) as counted)
               ) as peaks),
              (select array_agg(hour order by hour) from (
                 select extract(hour from occurred_at)::int as hour, count(*) as total
                 from crime_incidents group by 1
                 having count(*) = (select max(total) from (
                   select count(*) as total from crime_incidents
                   group by extract(hour from occurred_at)) as counted)
               ) as peaks)
            """
        )
    ).one()

    assert busiest in local_peaks, f"{busiest} bukan jam tersibuk menurut WIB ({local_peaks})"
    assert set(local_peaks) != set(utc_peaks), (
        "dataset tidak lagi membedakan WIB dan UTC — uji ini tumpul"
    )


def test_time_pattern_peak_cell_is_the_maximum_not_a_verdict(
    client: TestClient, session: Session
) -> None:
    body = _get(client, session, TIME_PATTERN)

    assert body["peak_cell"]["incidents"] == max(
        cell["incidents"] for row in body["days"] for cell in row["cells"]
    )
    # Rata-rata sel disebut sebagai pembanding aritmetika, bukan sebagai ambang.
    assert "bukan ambang" in body["cell_basis"]
    assert str(body["incidents"]) in body["cell_basis"]


def test_time_pattern_scope_is_enforced(client: TestClient, session: Session) -> None:
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    body = client.get(TIME_PATTERN, headers=_auth(client, officer)).json()

    scoped = session.execute(
        text(
            """
            select count(*) from crime_incidents ci
            join locations l on l.location_id = ci.location_id where l.polsek = :polsek
            """
        ),
        {"polsek": polsek},
    ).scalar_one()
    assert body["incidents"] == scoped
    assert (
        body["incidents"]
        < session.execute(text("select count(*) from crime_incidents")).scalar_one()
    )


# ----------------------------------------------------------------------------
# Perbandingan antarwilayah
# ----------------------------------------------------------------------------


def test_spatial_pattern_matrix_matches_direct_sql(client: TestClient, session: Session) -> None:
    body = _get(client, session, SPATIAL)

    cells = {
        f"{area['kecamatan']}|{cell['threat_type']}": cell["incidents"]
        for area in body["areas"]
        for cell in area["by_threat"]
        if cell["incidents"]
    }
    assert cells == _counts(
        session,
        """
        select l.kecamatan || '|' || ci.incident_type, count(*)
        from crime_incidents ci join locations l on l.location_id = ci.location_id
        group by 1
        """,
    )

    assert {area["kecamatan"]: area["incidents"] for area in body["areas"]} == _counts(
        session,
        """
        select l.kecamatan, count(*)
        from crime_incidents ci join locations l on l.location_id = ci.location_id
        group by 1
        """,
    )
    counts = [area["incidents"] for area in body["areas"]]
    assert counts == sorted(counts, reverse=True)


def test_spatial_pattern_uses_two_denominators_and_names_both(
    client: TestClient, session: Session
) -> None:
    """Satu sel memuat dua persentase; keduanya tidak berarti tanpa penyebutnya."""
    body = _get(client, session, SPATIAL)
    per_threat = {row["threat_type"]: row["incidents"] for row in body["threat_types"]}

    for area in body["areas"]:
        assert area["denominator"] == area["incidents"]
        assert area["share_percent"] == round(100 * area["incidents"] / body["denominator"], 1)
        for cell in area["by_threat"]:
            assert cell["share_of_area_percent"] == round(
                100 * cell["incidents"] / area["incidents"], 1
            )
            assert cell["share_of_threat_percent"] == round(
                100 * cell["incidents"] / per_threat[cell["threat_type"]], 1
            )

    assert "share_of_area_percent" in body["share_basis"]
    assert "share_of_threat_percent" in body["share_basis"]


def test_spatial_pattern_admits_it_compares_raw_counts(
    client: TestClient, session: Session
) -> None:
    """Tanpa data kependudukan, perbandingan ini tidak boleh mengaku sebagai angka rawan."""
    body = _get(client, session, SPATIAL)

    assert "bukan angka per penduduk" in body["rate_basis"]
    assert str(body["areas_compared"]) in body["comparison_basis"]


def test_spatial_pattern_states_when_there_is_nothing_to_compare(
    client: TestClient, session: Session
) -> None:
    """Pengguna Polsek hanya punya satu kecamatan — layar tidak boleh menyebutnya perbandingan."""
    polsek = session.scalar(select(Location.polsek).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    body = client.get(SPATIAL, headers=_auth(client, officer)).json()

    kecamatan = session.scalars(
        select(Location.kecamatan).where(Location.polsek == polsek).distinct()
    ).all()
    assert body["areas_compared"] == len(
        {row["kecamatan"] for row in body["areas"] if row["kecamatan"] in set(kecamatan)}
    )
    assert {area["kecamatan"] for area in body["areas"]} <= set(kecamatan)
    assert polsek in body["comparison_basis"]


# ----------------------------------------------------------------------------
# Otorisasi, validasi masukan, dan batas penafsiran — berlaku untuk ketiganya
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ANALYTICS_ENDPOINTS)
def test_analytics_requires_analytics_read(
    client: TestClient, session: Session, endpoint: str
) -> None:
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

    response = client.get(endpoint, headers=_auth(client, user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("endpoint", ANALYTICS_ENDPOINTS)
def test_analytics_unauthenticated_request_is_refused(client: TestClient, endpoint: str) -> None:
    assert client.get(endpoint).status_code == 401


@pytest.mark.parametrize("endpoint", ANALYTICS_ENDPOINTS)
def test_analytics_scoped_user_without_a_jurisdiction_is_refused(
    client: TestClient, session: Session, endpoint: str
) -> None:
    officer = _make_user(session, "Polsek", polsek=None)

    assert client.get(endpoint, headers=_auth(client, officer)).status_code == 403


@pytest.mark.parametrize("endpoint", ANALYTICS_ENDPOINTS)
def test_analytics_rejects_a_reversed_date_range(
    client: TestClient, session: Session, endpoint: str
) -> None:
    user = _make_user(session, "Administrator")

    response = client.get(
        f"{endpoint}?date_from=2025-06-01&date_to=2025-01-01", headers=_auth(client, user)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("endpoint", (TREND, TIME_PATTERN))
def test_analytics_rejects_an_unknown_threat_type(
    client: TestClient, session: Session, endpoint: str
) -> None:
    user = _make_user(session, "Administrator")

    response = client.get(f"{endpoint}?threat_type=TIDAK_ADA", headers=_auth(client, user))

    assert response.status_code == 400
    assert "CURANMOR" in response.json()["error"]["details"][0]["issue"]


def test_trend_rejects_an_absurdly_long_axis(client: TestClient, session: Session) -> None:
    """Rentang berasal dari pengguna; tanpa batas, sumbu bisa berisi ribuan bulan kosong."""
    user = _make_user(session, "Administrator")

    response = client.get(f"{TREND}?date_from=1800-01-01", headers=_auth(client, user))

    assert response.status_code == 400
    assert "240" in response.json()["error"]["message"]


@pytest.mark.parametrize("endpoint", ANALYTICS_ENDPOINTS)
def test_analytics_never_speaks_as_a_prediction(
    client: TestClient, session: Session, endpoint: str
) -> None:
    """Analisis deskriptif tidak boleh membawa skor risiko atau tingkat keyakinan.

    Begitu hitungan masa lalu diberi `confidence`, ia terbaca sebagai pernyataan tentang
    masa depan (CLAUDE.md §27).
    """
    response = client.get(endpoint, headers=_auth(client, _make_user(session, "Administrator")))

    serialized = response.text
    for forbidden in ("risk_score", "confidence", "forecast_horizon", "model_version"):
        assert forbidden not in serialized, (
            f"'{forbidden}' tidak boleh ada pada analisis deskriptif"
        )

    body = response.json()
    assert "bukan prediksi" in body["analysis_basis"]
    # Layar analitik harus menyebut kaitannya dengan Crime Pattern DNA agar pembaca tahu
    # keduanya bukan analisis yang sama.
    assert "crime-pattern-dna" in body["related_analysis_basis"]


@pytest.mark.parametrize("endpoint", ANALYTICS_ENDPOINTS)
def test_analytics_carries_the_source_that_produced_the_numbers(
    client: TestClient, session: Session, endpoint: str
) -> None:
    body = _get(client, session, endpoint)

    date_from, date_to, total = session.execute(
        text("select min(incident_date), max(incident_date), count(*) from crime_incidents")
    ).one()
    assert body["source"]["table"] == "crime_incidents"
    assert body["source"]["date_from"] == date_from.isoformat()
    assert body["source"]["date_to"] == date_to.isoformat()
    assert body["source"]["incidents"] == total


def test_analytics_agrees_with_crime_pattern_dna_on_the_same_numbers(
    client: TestClient, session: Session
) -> None:
    """Dua layar, satu sumber: angka yang sama harus benar-benar sama.

    Ini yang membenarkan pemakaian ulang agregasi `patterns.py` alih-alih menyalinnya —
    bila keduanya menyimpang, uji ini yang gagal lebih dulu, bukan pembaca paparan.
    """
    user = _make_user(session, "Administrator")
    headers = _auth(client, user)

    dna = client.get(
        "/api/v1/analytics/crime-pattern-dna?threat_type=CURANMOR", headers=headers
    ).json()
    trend = client.get(f"{TREND}?threat_type=CURANMOR", headers=headers).json()
    matrix = client.get(f"{TIME_PATTERN}?threat_type=CURANMOR", headers=headers).json()

    assert dna["profile"]["incidents"] == trend["incidents"] == matrix["incidents"]

    # Sebaran jam pada DNA adalah jumlah kolom matriks hari x jam.
    dna_hours = {
        bucket["key"]: bucket["incidents"]
        for row in dna["profile"]["when"]
        if row["id"] == "hour"
        for bucket in row["buckets"]
    }
    assert {str(row["hour"]): row["incidents"] for row in matrix["hours"]} == dna_hours
