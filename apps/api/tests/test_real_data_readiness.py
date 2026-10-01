"""Kesiapan sistem menampung data kejadian ASLI (Pusiknas, 30 September 2026).

Data sintetis selama ini selalu lengkap: setiap kejadian punya jam, setiap sel punya grid.
Data asli tidak. Test di sini menanam baris berbentuk data asli ke dalam transaksi yang
dibatalkan, lalu memastikan tidak ada satu pun jalur yang (1) menjatuhkan endpoint, atau
(2) diam-diam mengarang jam yang tidak pernah tercatat.
"""

from __future__ import annotations

import csv
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.seeding import csv_source as src
from prediksi_presisi_api.seeding.crime import seed_crime_data
from prediksi_presisi_api.seeding.master import SeedSummary, seed_police_units
from prediksi_presisi_api.seeding.paths import REPO_ROOT, SAMPLE_DATA_DIR
from prediksi_presisi_api.seeding.taxonomy import load_taxonomy
from prediksi_presisi_api.services import risk_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
RAW = (
    REPO_ROOT
    / "data"
    / "raw"
    / "Data_Kejadian_Curanmor_Curat_Curas_Polres_Metro_Jaksel_2023-Sep2026.xlsx"
)

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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _leader(session: Session) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == "Pimpinan"))
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
    return {"username": user.username}


def _auth(client: TestClient, who: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": who["username"], "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _incident_without_hour(session: Session) -> CrimeIncident:
    """Satu kejadian berbentuk data asli: tanpa jam, dengan kolom Laporan Polisi."""
    location = session.scalar(select(Location).limit(1))
    assert location is not None
    row = CrimeIncident(
        code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
        incident_type="CURANMOR",
        occurred_at=datetime(2025, 12, 30, 17, 0, tzinfo=UTC),  # tengah malam WIB 31 Des
        incident_date=date(2025, 12, 31),
        incident_time=None,
        time_known=False,
        location_id=location.location_id,
        location_type="Jalan Umum",
        modus="Merusak",
        target_type="Kendaraan bermotor",
        reported_at=datetime(2025, 12, 31, 3, 0, tzinfo=UTC),
        report_source="CITIZEN_REPORT",
        receiving_unit="Polsek Tebet",
        data_group="TRAIN",
        data_source="PUSIKNAS-UJI",
    )
    session.add(row)
    session.flush()
    return row


# --- 1. Jam kosong tidak menjatuhkan apa pun ---------------------------------------------


def test_the_crime_list_serves_an_incident_without_an_hour(
    client: TestClient, session: Session
) -> None:
    """Sebelum perbaikan, `.isoformat()` pada jam NULL menjatuhkan seluruh daftar dengan 500."""
    row = _incident_without_hour(session)
    headers = _auth(client, _leader(session))

    response = client.get(
        "/api/v1/crimes?page_size=200&date_from=2025-12-31&date_to=2025-12-31", headers=headers
    )
    assert response.status_code == 200, response.text

    served = next((r for r in response.json()["data"] if r["code"] == row.code), None)
    assert served is not None, "baris tanpa jam hilang dari daftar"
    assert served["incident_time"] is None
    assert served["time_known"] is False


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/analytics/crime-pattern-dna?threat_type=CURANMOR",
        "/api/v1/analytics/time-pattern?threat_type=CURANMOR",
        "/api/v1/analytics/trend",
        "/api/v1/dashboard/leadership",
    ],
)
def test_hour_patterns_survive_incidents_without_an_hour(
    client: TestClient, session: Session, path: str
) -> None:
    """`extract(hour, NULL)` menghasilkan NULL; `int(None)` lalu meledak. Setiap pola jam
    harus menyaring `time_known` — bukan karena jamnya nol, melainkan karena tidak ada."""
    _incident_without_hour(session)
    headers = _auth(client, _leader(session))

    response = client.get(path, headers=headers)
    assert response.status_code == 200, (path, response.text[:200])


def test_unknown_hours_never_shape_the_hour_pattern(session: Session) -> None:
    """Mesin penilaian membentuk pola jam HANYA dari kejadian yang jamnya tercatat.

    Mengisi jam kosong dengan 00:00 akan menumpuk 1.798 kejadian asli ke jendela dini
    hari — dan jam rawan Curanmor berpindah ke tengah malam tanpa satu pun kejadian
    nyata di sana.
    """
    before = risk_engine.collect_evidence(session).hours
    _incident_without_hour(session)
    after = risk_engine.collect_evidence(session).hours

    assert after == before, "kejadian tanpa jam ikut membentuk pola jam"


# --- 2. Seeder sumber `processed` ---------------------------------------------------------


def test_processed_source_loads_incidents_without_hours_and_skips_synthetic_tables(
    session: Session, tmp_path: Path
) -> None:
    """Direktori hasil impor hanya berisi kejadian dan lokasi. Tabel sintetis dilewati
    dengan catatan, bukan dicari lalu menggagalkan seed."""
    (tmp_path / "locations.csv").write_text(
        "location_id,polsek,kecamatan,kelurahan,grid_id,grid_size_m,latitude,longitude,location_type\n"
        "LOC-KEL-uji,Polsek Tebet,Tebet,Manggarai,kel:uji-manggarai,0,-6.21,106.85,KELURAHAN\n",
        encoding="utf-8",
    )
    with (tmp_path / "crime_incidents.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "incident_id",
                "incident_type",
                "incident_date",
                "incident_time",
                "polsek",
                "kecamatan",
                "kelurahan",
                "grid_id",
                "latitude",
                "longitude",
                "location_type",
                "modus",
                "target_type",
                "status",
                "reported_at",
                "report_lag_hours",
                "report_source",
                "receiving_unit",
                "data_group",
                "street",
                "grid_500m",
                "data_source",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "incident_id": "KJD-UJI-00001",
                "incident_type": "CURANMOR",
                "incident_date": "2026-01-05",
                "incident_time": "",
                "polsek": "Polsek Tebet",
                "kecamatan": "Tebet",
                "kelurahan": "Manggarai",
                "grid_id": "kel:uji-manggarai",
                "latitude": "",
                "longitude": "",
                "location_type": "Jalan Umum",
                "modus": "Merusak",
                "target_type": "Kendaraan bermotor",
                "status": "",
                "reported_at": "2026-01-06T08:00:00+07:00",
                "report_lag_hours": "20.0",
                "report_source": "Laporan masyarakat",
                "receiving_unit": "Polsek Tebet",
                "data_group": "Data uji",
                "street": "",
                "grid_500m": "",
                "data_source": "PUSIKNAS-UJI",
            }
        )

    taxonomy = load_taxonomy()
    src.use_directory(tmp_path)
    try:
        from prediksi_presisi_api.seeding.master import seed_locations

        summary = SeedSummary()
        seed_locations(session, summary)
        seed_police_units(session, taxonomy, summary)
        summary.merge(seed_crime_data(session, taxonomy))
    finally:
        src.use_directory(SAMPLE_DATA_DIR)

    loaded = session.scalar(select(CrimeIncident).where(CrimeIncident.code == "KJD-UJI-00001"))
    assert loaded is not None
    assert loaded.time_known is False and loaded.incident_time is None
    assert loaded.data_group == "TEST" and loaded.report_source == "CITIZEN_REPORT"
    assert loaded.report_lag_hours == 20.0
    assert "dilewati" in summary.notes.get("police_units", "")
    assert "dilewati" in summary.notes.get("intelligence_reports", "")
    assert "dilewati" in summary.notes.get("patrol_activity", "")


# --- 3. Pipeline impor memvalidasi dirinya terhadap rekap resmi --------------------------


@pytest.mark.skipif(not RAW.exists(), reason="berkas sumber Pusiknas tidak ada di mesin ini")
def test_import_pipeline_reproduces_the_official_totals(tmp_path: Path) -> None:
    """Angka hasil impor harus sama dengan rekap resmi — selisih satu pun menggagalkan impor."""
    import importlib.util
    import json

    spec = importlib.util.spec_from_file_location(
        "pusiknas", REPO_ROOT / "scripts" / "import" / "pusiknas.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    df = module.read_incidents()
    incidents, tally = module.build_incidents(df)
    assert module.validate(incidents) == []
    assert len(incidents) == 8203
    assert tally == {
        "tanpa_jam": 1798,
        "tanpa_tanggal_kejadian": 10,
        "tanpa_kelurahan": 413,
        "koordinat": 1395,
    }
    assert len(module.build_locations(df)) == 75
    manifest = json.loads((REPO_ROOT / "data" / "processed" / "MANIFEST.json").read_text())
    assert manifest["incidents"] == 8203
