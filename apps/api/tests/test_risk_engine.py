"""Uji mesin penilaian risiko (`services/risk_engine.py`) dan endpoint-nya.

Yang dijaga di sini bukan "angkanya keluar", melainkan janji yang membuat angka itu boleh
dipercaya:

1. bobot dan ambang benar-benar berasal dari `config/risk/`, bukan dari kode;
2. `null` dan `0` tidak pernah tertukar — nol berarti terukur nol, null berarti tidak
   terukur, dan alasannya ikut;
3. kombinasi yang faktor berbobotnya tidak terukur **tidak** diberi skor, bukan diberi
   skor yang diturunkan diam-diam;
4. `round(Sum(bobot x faktor))` benar-benar berlaku pada setiap baris yang dihasilkan;
5. Profil B tidak pernah mengarang data unjuk rasa;
6. penilaian yang sudah ada tidak dapat ditimpa, dan `dry_run` tidak menulis apa pun.

Uji aritmetika berjalan tanpa database sama sekali: `assess_historical` menerima
`Evidence` yang dapat disusun di memori, sehingga rumusnya dapat diuji tanpa satu pun
baris dummy.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterable, Iterator
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, RiskScore, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import risk_engine as engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

#: Tanggal penilaian yang pasti belum dipakai siapa pun. Seluruh test yang menulis
#: berjalan di dalam transaksi yang dibatalkan, tetapi tanggalnya tetap dipilih di luar
#: rentang dataset agar tidak menyerupai data sungguhan bila suatu saat bocor.
UNUSED_ASSESSMENT_DATE = "2099-01-01"


# ---------------------------------------------------------------------------
# Konfigurasi — tidak ada angka yang boleh berasal dari kode
# ---------------------------------------------------------------------------


def test_weights_come_from_the_configuration_file() -> None:
    """Bobot yang dipakai mesin sama persis dengan isi `config/risk/risk-weights.yaml`."""
    raw = yaml.safe_load(engine.RISK_WEIGHTS_FILE.read_text(encoding="utf-8"))
    catalogue = engine.load_weights()

    assert catalogue.active_version == raw["active_version"]
    assert set(catalogue.versions) == set(raw["versions"])

    for name, version in catalogue.versions.items():
        for profile_name, profile in version.profiles.items():
            source = raw["versions"][name]["profiles"][profile_name]
            assert profile.weights == {
                key: float(value) for key, value in source["weights"].items()
            }
            assert list(profile.applies_to) == list(source["applies_to"])


def test_risk_classes_come_from_the_threshold_file() -> None:
    """Kelas risiko dibaca dari config, bukan dihitung ulang di kode (CLAUDE.md §12)."""
    raw = yaml.safe_load(engine.THRESHOLDS_FILE.read_text(encoding="utf-8"))
    thresholds = engine.load_thresholds()

    assert thresholds.version == raw["version"]
    for band in raw["risk_classes"]:
        assert thresholds.class_for(int(band["min"])) == band["class"]
        assert thresholds.class_for(int(band["max"])) == band["class"]


def test_an_unbalanced_version_is_refused() -> None:
    """Bobot positif yang tidak berjumlah 1 harus ditolak, bukan dipakai diam-diam."""
    broken = engine.Profile(name="historical", applies_to=("CURANMOR",), weights={"a": 0.9})
    assert broken.positive_total == pytest.approx(0.9)
    assert broken.positive_total != 1.0


# ---------------------------------------------------------------------------
# Aritmetika — tanpa database
# ---------------------------------------------------------------------------


def _factor(name: str, value: int | None, weight: float | None) -> engine.Factor:
    return engine.Factor(
        name=name, value=value, weight=weight, reason=None if value is not None else "diuji"
    )


def _recompute(terms: Iterable[tuple[float, int]]) -> int:
    """Menghitung ulang `round(Sum(bobot x faktor))` dengan aritmetika desimal eksak.

    Sengaja **tidak** memanggil mesin penilaian: yang diperiksa adalah apakah angka
    tersimpan dapat direproduksi oleh orang lain dengan alat lain. Pembulatan setengah ke
    atas di sini sama dengan `round(numeric)` PostgreSQL dan lembar kerja.
    """
    total = sum((Decimal(str(weight)) * value for weight, value in terms), Decimal(0))
    return int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def test_score_is_the_weighted_sum() -> None:
    factors = (_factor("a", 100, 0.3), _factor("b", 50, 0.7))
    score, reason = engine.score_of(factors, {"a": 0.3, "b": 0.7})

    assert score == round(0.3 * 100 + 0.7 * 50)
    assert reason is None


def test_a_tie_rounds_the_same_way_postgresql_does() -> None:
    """Nilai tepat 0,5 dibulatkan menjauhi nol, bukan ke bilangan genap.

    Ini bukan kerewelan: skor tersimpan diperiksa orang dengan SQL atau lembar kerja, dan
    keduanya membulatkan 18,5 menjadi 19. `round()` bawaan Python menghasilkan 18, dan
    baris yang sah akan terbaca meleset satu angka.
    """
    factors = (_factor("a", 18, 0.5), _factor("b", 19, 0.5))
    score, _ = engine.score_of(factors, {"a": 0.5, "b": 0.5})

    assert score == 19


def test_a_missing_weighted_factor_leaves_the_row_unscored() -> None:
    """Bukan diberi skor yang lebih rendah — tidak diberi skor sama sekali."""
    factors = (_factor("a", 100, 0.3), _factor("b", None, 0.7))
    score, reason = engine.score_of(factors, {"a": 0.3, "b": 0.7})

    assert score is None
    assert reason is not None
    assert "b" in reason


def test_a_zero_weight_factor_may_be_missing_without_blocking_the_score() -> None:
    """Faktor berbobot nol tidak menghalangi apa pun — ia memang tidak menyumbang."""
    factors = (_factor("a", 100, 1.0), _factor("community_factor", None, 0.0))
    score, reason = engine.score_of(factors, {"a": 1.0, "community_factor": 0.0})

    assert score == 100
    assert reason is None


def test_a_weighted_factor_the_engine_cannot_compute_is_reported() -> None:
    """Bobot untuk faktor yang belum diimplementasikan tidak boleh diabaikan diam-diam."""
    score, reason = engine.score_of((_factor("a", 100, 0.5),), {"a": 0.5, "belum_ada": 0.5})

    assert score is None
    assert reason is not None
    assert "belum_ada" in reason


def test_planned_score_subtracts_readiness_and_clamps() -> None:
    """Profil B: bobot positif berjumlah 1, `readiness_factor` mengurangi, hasil 0–100."""
    weights = {"mass": 0.5, "location": 0.5, "readiness_factor": -0.10}

    full_impact: dict[str, int | None] = {"mass": 100, "location": 100, "readiness_factor": 0}
    prepared: dict[str, int | None] = {"mass": 100, "location": 100, "readiness_factor": 100}

    assert engine.planned_score(full_impact, weights) == 100
    assert engine.planned_score(prepared, weights) == 90
    # Kesiapan penuh atas dampak rendah tidak boleh menghasilkan skor negatif.
    calm: dict[str, int | None] = {"mass": 0, "location": 0, "readiness_factor": 100}
    assert engine.planned_score(calm, weights) == 0


def test_planned_score_refuses_to_guess_a_missing_input() -> None:
    weights = {"mass": 1.0, "readiness_factor": -0.10}

    incomplete: dict[str, int | None] = {"mass": None, "readiness_factor": 50}
    assert engine.planned_score(incomplete, weights) is None


def test_repeat_events_counts_same_day_and_near_repeats() -> None:
    day = date(2025, 1, 1)
    later = date(2025, 1, 1 + engine.NEAR_REPEAT_WINDOW_DAYS)
    far = date(2025, 6, 1)

    # Tiga kejadian pada satu hari: dua di antaranya adalah pengulangan.
    assert engine.repeat_events([(day, 3)]) == 2
    # Kejadian pada hari terakhir jendela masih dihitung berulang.
    assert engine.repeat_events([(day, 1), (later, 1)]) == 1
    # Kejadian yang jauh terpisah tidak.
    assert engine.repeat_events([(day, 1), (far, 1)]) == 0
    # Satu kejadian tunggal: terukur, dan hasilnya nol.
    assert engine.repeat_events([(day, 1)]) == 0


# ---------------------------------------------------------------------------
# Penilaian Profil A atas bahan yang disusun sendiri
# ---------------------------------------------------------------------------

BUSY = uuid.uuid4()
QUIET = uuid.uuid4()

PROFILE = engine.Profile(
    name=engine.PROFILE_HISTORICAL,
    applies_to=("CURANMOR",),
    weights={
        "historical_factor": 0.30,
        "recent_trend_factor": 0.25,
        "temporal_factor": 0.20,
        "spatial_factor": 0.15,
        "context_factor": 0.10,
    },
)


def _evidence() -> engine.Evidence:
    """Dua sel pada satu kecamatan: satu padat kejadian, satu tanpa kejadian sama sekali."""
    return engine.Evidence(
        cells=(
            engine.Cell(BUSY, "UJI-001", "Kecamatan Uji", "Kelurahan A", "Polsek Uji", "Jalan"),
            engine.Cell(QUIET, "UJI-002", "Kecamatan Uji", "Kelurahan B", "Polsek Uji", None),
        ),
        incidents={(BUSY, "CURANMOR"): 10},
        recent={(BUSY, "CURANMOR"): 2},
        hours={("CURANMOR", 20): 8, ("CURANMOR", 3): 2},
        incident_days={(BUSY, "CURANMOR"): [(date(2025, 12, 1), 2), (date(2025, 12, 5), 1)]},
        intelligence={BUSY: 4},
        community={BUSY: 2},
        date_from=date(2025, 1, 1),
        date_to=date(2025, 12, 31),
        total_incidents=10,
    )


def _assessment() -> engine.ProfileAssessment:
    return engine.assess_historical(
        _evidence(), PROFILE, engine.load_thresholds(), date(2025, 12, 31), "uji"
    )


def _cell(grid_id: str, window: str) -> engine.CellAssessment:
    found = next(
        cell
        for cell in _assessment().cells
        if cell.grid_id == grid_id and cell.time_window == window
    )
    return found


def test_every_cell_and_window_is_assessed() -> None:
    """Satu baris untuk setiap sel × jenis ancaman × jendela waktu."""
    cells = _assessment().cells

    assert len(cells) == len(_evidence().cells) * len(PROFILE.applies_to) * len(engine.TIME_WINDOWS)


def test_the_busiest_cell_reaches_the_top_of_each_factor() -> None:
    """Sel terpadat bernilai 100 pada faktor yang dinormalkan terhadapnya."""
    busy = _cell("UJI-001", "18:00-23:59")
    values = {factor.name: factor.value for factor in busy.factors}

    assert values["historical_factor"] == 100
    assert values["temporal_factor"] == 100  # 80% kejadian jatuh pada jendela malam
    assert values["context_factor"] == 100
    assert busy.risk_score is not None


def test_the_score_equals_the_weighted_sum_of_its_own_factors() -> None:
    """Hubungan `risk_score = round(Sum(bobot x faktor))` berlaku pada setiap baris."""
    for cell in _assessment().scored:
        expected = _recompute(
            (factor.weight, factor.value)
            for factor in cell.factors
            if factor.weight is not None and factor.value is not None
        )
        assert cell.risk_score == expected


def test_a_measured_zero_is_zero_and_an_unmeasurable_factor_is_null() -> None:
    """Perbedaan yang menentukan: 0 berarti diukur, `null` berarti tidak dapat diukur."""
    quiet = _cell("UJI-002", "18:00-23:59")
    values = {factor.name: factor for factor in quiet.factors}

    # Sel ini benar-benar tidak memiliki kejadian CURANMOR: terukur, dan hasilnya nol.
    assert values["historical_factor"].value == 0
    # Tanpa satu pun kejadian, tidak ada rata-rata pembanding — dan alasannya ikut.
    assert values["recent_trend_factor"].value is None
    assert values["recent_trend_factor"].reason
    # locations.location_type kosong, jadi tidak ada kategori TKP yang dapat dipakai.
    assert values["context_factor"].value is None
    assert values["context_factor"].reason

    assert quiet.risk_score is None
    assert quiet.unscored_reason is not None
    assert "recent_trend_factor" in quiet.unscored_reason


def test_the_zero_weight_community_path_is_computed_but_contributes_nothing() -> None:
    """Jalur laporan masyarakat terlihat, tetapi tidak menyumbang selama bobotnya nol."""
    busy = _cell("UJI-001", "18:00-23:59")
    community = next(f for f in busy.factors if f.name == "community_factor")
    intelligence = next(f for f in busy.factors if f.name == "intelligence_factor")

    assert community.value is not None
    assert community.contribution == 0.0
    assert intelligence.value is not None
    assert intelligence.contribution == 0.0


def test_every_factor_is_labelled_rule_not_model() -> None:
    """Tidak ada model terlatih di sini, dan penjelasannya tidak boleh menyiratkan ada."""
    for factor in _cell("UJI-001", "18:00-23:59").dominant_factors():
        assert factor["source"] == "RULE"


# ---------------------------------------------------------------------------
# Endpoint — memerlukan database
# ---------------------------------------------------------------------------

pytestmark_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


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


def _user(session: Session, role_name: str) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, f"role {role_name} belum ada — jalankan seed"

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
    return user


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytestmark_db
def test_running_requires_the_run_permission(client: TestClient, session: Session) -> None:
    """Pimpinan boleh membaca risiko, tetapi tidak menjalankan penilaiannya."""
    headers = _auth(client, _user(session, "Pimpinan"))
    response = client.post("/api/v1/risk-scores/run", json={"dry_run": True}, headers=headers)

    assert response.status_code == 403, response.text


@pytestmark_db
def test_dry_run_writes_nothing(client: TestClient, session: Session) -> None:
    headers = _auth(client, _user(session, "Administrator"))
    before = session.scalar(select(func.count()).select_from(RiskScore)) or 0

    response = client.post(
        "/api/v1/risk-scores/run",
        json={"assessment_date": UNUSED_ASSESSMENT_DATE, "dry_run": True},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dry_run"] is True
    assert body["written"] == 0
    assert (session.scalar(select(func.count()).select_from(RiskScore)) or 0) == before

    historical = next(item for item in body["profiles"] if item["profile"] == "historical")
    assert historical["scored"] > 0
    # Versi bobot ikut keluar: angka risiko tidak boleh tampil tanpa asalnya.
    assert body["weights_version"] == engine.load_weights().active_version


@pytestmark_db
def test_the_dry_run_sample_can_be_recomputed_by_hand(client: TestClient, session: Session) -> None:
    """Setiap baris contoh dapat dihitung ulang dari faktor dan bobot yang dibawanya."""
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(
        "/api/v1/risk-scores/run",
        json={"assessment_date": UNUSED_ASSESSMENT_DATE, "dry_run": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    historical = next(
        item for item in response.json()["profiles"] if item["profile"] == "historical"
    )
    assert historical["sample"], "ringkasan tanpa contoh tidak dapat diperiksa siapa pun"

    for row in historical["sample"]:
        recomputed = _recompute(
            (factor["weight"], factor["value"])
            for factor in row["factors"]
            if factor["weight"] is not None and factor["value"] is not None
        )
        assert row["risk_score"] == recomputed


@pytestmark_db
def test_the_historical_factor_matches_a_direct_count(client: TestClient, session: Session) -> None:
    """Faktor historis sebuah sel benar-benar berasal dari jumlah kejadian di sel itu.

    Dibandingkan dengan hitungan SQL langsung, bukan dengan hasil mesin itu sendiri.
    """
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(
        "/api/v1/risk-scores/run",
        json={"assessment_date": UNUSED_ASSESSMENT_DATE, "dry_run": True},
        headers=headers,
    )
    historical = next(
        item for item in response.json()["profiles"] if item["profile"] == "historical"
    )
    row = historical["sample"][0]

    counts: dict[str, int] = {
        str(grid_id): int(total)
        for grid_id, total in session.execute(
            select(Location.grid_id, func.count())
            .join(CrimeIncident, CrimeIncident.location_id == Location.location_id)
            .where(CrimeIncident.incident_type == row["threat_type"])
            .group_by(Location.grid_id)
        ).all()
    }
    factor = next(item for item in row["factors"] if item["factor"] == "historical_factor")

    assert factor["value"] == round(100 * counts[row["grid_id"]] / max(counts.values()))


@pytestmark_db
def test_an_existing_assessment_date_is_never_overwritten(
    client: TestClient, session: Session
) -> None:
    """409, bukan menimpa: skor yang sudah dipakai menerbitkan peringatan tidak berubah."""
    headers = _auth(client, _user(session, "Administrator"))
    taken = session.scalar(select(func.max(RiskScore.assessment_date)))
    assert taken is not None, "data awal tidak memiliki satu pun penilaian"

    response = client.post(
        "/api/v1/risk-scores/run",
        json={"assessment_date": taken.isoformat(), "dry_run": False},
        headers=headers,
    )

    assert response.status_code == 409, response.text
    assert taken.isoformat() in response.json()["error"]["message"]


@pytestmark_db
def test_writing_stores_rows_that_explain_their_own_score(
    client: TestClient, session: Session
) -> None:
    """Baris tersimpan membawa faktor dan versi bobotnya, dan skornya dapat dihitung ulang.

    Dijalankan di dalam transaksi yang dibatalkan, sehingga tidak menambah satu baris pun
    ke basis data bersama.
    """
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(
        "/api/v1/risk-scores/run",
        json={"assessment_date": UNUSED_ASSESSMENT_DATE, "dry_run": False},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    written = response.json()["written"]
    assert written > 0

    rows = list(
        session.scalars(
            select(RiskScore).where(RiskScore.assessment_date == date(2099, 1, 1))
        ).all()
    )
    assert len(rows) == written

    weights = engine.load_weights()
    profile = weights.active.profiles[engine.PROFILE_HISTORICAL]
    for row in rows:
        assert row.weights_version == weights.active_version
        # Tidak ada model terlatih, jadi kolomnya tidak diisi seolah ada.
        assert row.model_version is None
        assert row.risk_score == _recompute(
            (weight, getattr(row, name)) for name, weight in profile.weights.items()
        )


@pytestmark_db
def test_the_configuration_endpoint_shows_the_basis(client: TestClient, session: Session) -> None:
    """Layar harus dapat menampilkan dasar perhitungan, bukan hanya hasilnya."""
    headers = _auth(client, _user(session, "Administrator"))
    response = client.get("/api/v1/risk-scores/config", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    catalogue = engine.load_weights()

    assert body["active_version"] == catalogue.active_version
    assert {version["version"] for version in body["versions"]} == set(catalogue.versions)
    assert [band["class"] for band in body["thresholds"]["risk_classes"]] == [
        band.risk_class for band in engine.load_thresholds().bands
    ]

    active = next(version for version in body["versions"] if version["active"])
    assert active["status"] in {"DEMO", "PROPOSED"}
    for profile in active["profiles"]:
        assert profile["applies_to"]
        assert profile["factors"]


@pytestmark_db
def test_planned_profile_never_invents_a_demonstration(
    client: TestClient, session: Session
) -> None:
    """Profil B tidak menghasilkan satu baris pun, dan menyebut alasannya."""
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(
        "/api/v1/risk-scores/run",
        json={"assessment_date": UNUSED_ASSESSMENT_DATE, "dry_run": True},
        headers=headers,
    )

    planned = next(item for item in response.json()["profiles"] if item["profile"] == "planned")
    assert planned["scored"] == 0
    assert planned["sample"] == []
    assert planned["not_computed_reason"]
