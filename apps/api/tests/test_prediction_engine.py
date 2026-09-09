"""Uji mesin prediksi (`services/prediction_engine.py`) dan endpoint AI Prediction Center.

Yang dijaga di sini bukan "prediksinya keluar", melainkan janji yang membuat prediksi itu
boleh dipercaya:

1. tidak ada klaim model terlatih — `model_version` menyebut versi aturan, seluruh
   `dominant_factors` berlabel `RULE`, dan kata "model" tidak dipakai sebagai sumber;
2. skor prediksi dapat ditelusuri ke baris `risk_scores` yang menjadi dasarnya, dan
   sumbangan tiap faktor menjumlah kembali ke skor itu;
3. `confidence` punya dasar yang dapat dihitung ulang, dan dasar yang tipis menghasilkan
   angka rendah beserta alasannya — bukan angka yang dikarang;
4. kombinasi tanpa dasar **tidak** diprediksi, bukan diprediksi dengan skor tebakan;
5. `dry_run` tidak menulis apa pun, tanggal + horizon yang sudah terpakai ditolak 409,
   dan prediksi baru berstatus `DRAFT`;
6. publikasi adalah tindakan tersendiri dengan kewenangan sendiri, dan tidak dapat
   diulang atas prediksi yang sudah terbit.

Uji aritmetika dan penentuan jendela berjalan tanpa database sama sekali.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, Location, Prediction, RiskScore, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock
from prediksi_presisi_api.services import prediction_engine as engine
from prediksi_presisi_api.services import risk_engine as risk

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

#: Tanggal prediksi yang pasti belum dipakai siapa pun. Seluruh test yang menulis berjalan
#: di dalam transaksi yang dibatalkan, tetapi tanggalnya tetap dipilih jauh di luar rentang
#: dataset agar tidak menyerupai data sungguhan bila suatu saat bocor.
UNUSED_PREDICTION_DATE = "2099-01-01"

#: Horizon terpendek dipakai pada test yang menulis: satu jendela per kombinasi sudah cukup
#: membuktikan jalurnya, tanpa membangun ribuan baris di dalam transaksi uji.
SHORT_HORIZON = "6H"


# ---------------------------------------------------------------------------
# Jendela yang diprediksi — tanpa database
# ---------------------------------------------------------------------------

WHEN = date(2025, 12, 31)


def test_horizon_is_a_distance_not_a_span() -> None:
    """Setiap horizon menghasilkan TEPAT empat bin 6 jam — satu hari sasaran, bukan rentang.

    Uji ini gagal bila horizon kembali dibaca sebagai panjang rentang: pembacaan itu
    menghasilkan 1 jendela untuk 6H dan 28 untuk 7D, dan menggandakan seluruh keluaran
    tanpa ada yang menyadarinya.
    """
    for horizon in engine.HORIZON_OFFSETS:
        windows = engine.horizon_windows(WHEN, horizon)

        assert len(windows) == len(risk.TIME_WINDOWS) == 4
        assert {label for label, _start, _end in windows} == set(risk.TIME_WINDOWS)
        # Panjang jendela SELALU 6 jam, berapa pun horizonnya.
        for _label, start, end in windows:
            assert end - start == timedelta(hours=6)
        # Seluruh jendela jatuh pada satu hari sasaran yang sama.
        assert len({start.date() for _label, start, _end in windows}) == 1


def test_the_target_day_moves_with_the_horizon() -> None:
    """Jarak dari `prediction_date` ke hari sasaran = horizon dibulatkan ke bawah ke hari."""
    assert engine.horizon_day_offset("6H") == 0
    assert engine.horizon_day_offset("12H") == 0
    assert engine.horizon_day_offset("24H") == 1
    assert engine.horizon_day_offset("3D") == 3
    assert engine.horizon_day_offset("7D") == 7

    for horizon, offset in (("6H", 0), ("12H", 0), ("24H", 1), ("3D", 3), ("7D", 7)):
        for _label, start, _end in engine.horizon_windows(WHEN, horizon):
            assert start.date() == WHEN + timedelta(days=offset)

    # 7D pada 31 Desember 2025 jatuh pada 7 Januari 2026 — pergantian tahun ikut benar.
    assert engine.horizon_windows(WHEN, "7D")[0][1] == datetime(
        2026, 1, 7, 0, 0, tzinfo=clock.JAKARTA
    )


def test_six_and_twelve_hours_land_on_the_same_windows() -> None:
    """Keterbatasan yang dinyatakan terbuka, bukan disembunyikan — lihat `HORIZON_BASIS`.

    `prediction_date` bertipe DATE, sehingga 6H dan 12H sama-sama berjarak 0 hari. Data
    seed pun tidak membedakan keduanya. Uji ini merekam kenyataan itu supaya perubahannya
    kelak terlihat, bukan untuk membenarkannya.
    """
    assert engine.horizon_windows(WHEN, "6H") == engine.horizon_windows(WHEN, "12H")


def test_window_bounds_match_the_risk_scoring_engine() -> None:
    """Batas jendela sama persis dengan `risk_scores`, sehingga keduanya dapat disandingkan."""
    for label, start, end in engine.horizon_windows(WHEN, "24H"):
        assert (start, end) == risk._window_bounds(start.date(), label)
        assert end - start == timedelta(hours=6)


def test_an_unknown_horizon_is_refused_rather_than_guessed() -> None:
    with pytest.raises(engine.PredictionEngineError) as error:
        engine.horizon_windows(WHEN, "48H")

    assert "48H" in str(error.value)


# ---------------------------------------------------------------------------
# Confidence — tanpa database
# ---------------------------------------------------------------------------


def test_confidence_is_the_normalised_evidence_count() -> None:
    """Angkanya dapat dihitung ulang dari alasan yang dibawanya sendiri."""
    value, reason = engine.confidence_of(7, 28, "CURANMOR", "18:00-23:59")

    assert value == 25
    assert "7" in reason
    assert "28" in reason
    assert "25" in reason


def test_thin_evidence_yields_low_confidence_with_its_reason() -> None:
    """Nol kejadian penopang berarti confidence nol — dan sebabnya ikut dikembalikan."""
    value, reason = engine.confidence_of(0, 28, "CURANMOR", "18:00-23:59")

    assert value == 0
    assert "tidak ada kejadian" in reason
    assert "tipis" in reason


def test_confidence_without_any_comparator_is_zero_not_invented() -> None:
    """Tanpa pembanding, angka confidence tidak dikarang — ia nol beserta alasannya."""
    value, reason = engine.confidence_of(0, 0, "UNJUK_RASA", "06:00-12:00")

    assert value == 0
    assert "tidak ada pembanding" in reason


def test_confidence_never_leaves_the_zero_to_hundred_scale() -> None:
    assert engine.confidence_of(28, 28, "CURAT", "00:00-06:00")[0] == 100
    assert 0 <= engine.confidence_of(1, 464, "CURAT", "00:00-06:00")[0] <= 100


# ---------------------------------------------------------------------------
# Penjelasan — tanpa database
# ---------------------------------------------------------------------------


def _baseline(score: int = 63) -> engine.Baseline:
    return engine.Baseline(
        risk_score_id=uuid.uuid4(),
        code="RS-99999",
        assessment_date=date(2025, 12, 18),
        risk_score=score,
        risk_class="MODERATE",
        weights_version="uji",
        factors={
            "historical_factor": 60,
            "recent_trend_factor": 53,
            "temporal_factor": 72,
            "spatial_factor": 70,
            "context_factor": 68,
        },
    )


def _forecast(baseline: engine.Baseline | None) -> engine.Forecast:
    moment = datetime(2025, 12, 19, 18, 0, tzinfo=UTC)
    return engine.Forecast(
        location_id=uuid.uuid4(),
        grid_id="JKS-001",
        kecamatan="Tebet",
        kelurahan="Manggarai",
        polsek="Tebet",
        threat_type="CURANMOR",
        time_window="18:00-23:59",
        window_start=moment,
        window_end=moment,
        baseline=baseline,
        risk_score=None if baseline is None else baseline.risk_score,
        confidence=None if baseline is None else 70,
        confidence_reason="diuji",
        supporting_incidents=3,
        dominant_factors=(),
        not_predicted_reason=None if baseline is not None else "tanpa dasar",
    )


def test_predictions_are_never_given_a_risk_class() -> None:
    """Keputusan pemilik proyek 9 September 2026: prediksi tetap skor mentah.

    Sampai hari itu mesin ini memanggil `thresholds.class_for(...)` untuk tiap prediksi,
    sehingga layar Prediction Center menampilkan "95 CRITICAL" — tangga yang ditetapkan
    bagi PENILAIAN keadaan berjalan dipinjamkan kepada PERKIRAAN. Skor prediksi 80 tidak
    menyatakan hal yang sama dengan skor penilaian 80, dan menyamakan keduanya membuat
    perkiraan terbaca sebagai keadaan.

    Yang diperiksa adalah bentuk keluarannya, bukan sekadar ketiadaan atribut: kunci
    `risk_class` tidak boleh muncul dengan nama apa pun yang menyiratkan ia milik prediksi.
    """
    row = _forecast(_baseline()).as_dict()

    assert "risk_class" not in row
    assert row["risk_score"] == 63
    # Kelas penilaian dasarnya tetap terbawa — dengan nama yang menyebut milik siapa ia.
    assert row["baseline_risk_class"] == "MODERATE"


def test_a_forecast_without_a_baseline_reports_no_class_at_all() -> None:
    """Tanpa penilaian dasar tidak ada kelas untuk dilaporkan, dan tidak boleh dikarang."""
    row = _forecast(None).as_dict()

    assert row["baseline_risk_class"] is None
    assert row["risk_score"] is None


def test_every_dominant_factor_is_labelled_rule() -> None:
    """Tidak ada model terlatih, dan penjelasannya tidak boleh menyiratkan ada."""
    factors = engine._dominant_factors(_baseline(), {"historical_factor": 0.3}, None, "alasan", 3)

    assert factors
    for factor in factors:
        assert factor["source"] == "RULE"


def test_the_confidence_basis_travels_with_the_row() -> None:
    """Angka confidence tidak boleh tersimpan tanpa dasar yang dapat diperiksa."""
    factors = engine._dominant_factors(_baseline(), {}, "tidak ada bobot", "7 kejadian", 7)
    carrier = next(item for item in factors if item["factor"] == engine.CONFIDENCE_FACTOR)

    assert carrier["value"] == 7
    assert carrier["reason"] == "7 kejadian"
    # Dasar confidence tidak menyumbang apa pun pada risk_score.
    assert carrier["contribution"] == 0.0


def test_factor_contributions_add_back_up_to_the_baseline_score() -> None:
    """Sumbangan tiap faktor menjumlah kembali ke skor — syarat WHY yang dapat diperiksa."""
    weights = {
        "historical_factor": 0.30,
        "recent_trend_factor": 0.25,
        "temporal_factor": 0.20,
        "spatial_factor": 0.15,
        "context_factor": 0.10,
    }
    baseline = _baseline()
    factors = engine._dominant_factors(baseline, weights, None, "alasan", 1)

    total = sum(
        (
            Decimal(str(weights[name])) * value
            for name, value in baseline.factors.items()
            if value is not None
        ),
        Decimal(0),
    )
    expected = int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    assert round(sum(float(item["contribution"]) for item in factors)) == expected


def test_factors_are_ordered_by_their_contribution() -> None:
    """Yang paling menentukan tampil lebih dulu; dasar confidence selalu di akhir."""
    weights = {"historical_factor": 0.9, "context_factor": 0.1}
    factors = engine._dominant_factors(_baseline(), weights, None, "alasan", 1)

    assert factors[0]["factor"] == "historical_factor"
    assert factors[-1]["factor"] == engine.CONFIDENCE_FACTOR


def test_an_unknown_weights_version_reports_itself_instead_of_guessing() -> None:
    weights, reason = engine._weights_for(risk.load_weights(), "versi-yang-tidak-ada")

    assert weights == {}
    assert reason is not None
    assert "versi-yang-tidak-ada" in reason


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


def _run(
    client: TestClient, headers: dict[str, str], **payload: object
) -> tuple[int, dict[str, Any]]:
    body = {"prediction_date": UNUSED_PREDICTION_DATE, "horizon": SHORT_HORIZON, **payload}
    response = client.post("/api/v1/predictions/run", json=body, headers=headers)
    return response.status_code, response.json()


@pytestmark_db
def test_horizon_matches_the_predictions_already_in_the_database(session: Session) -> None:
    """Pembacaan horizon dikunci terhadap prediksi yang SUDAH ADA, bukan terhadap dokumen.

    Untuk setiap baris `predictions`, jendela yang dihitung mesin ini dari
    (`prediction_date`, `forecast_horizon`) harus MEMUAT jendela baris itu apa adanya.
    Prediksi baru dengan demikian sebaris dengan yang lama, dan keduanya dapat
    disandingkan pada peta maupun evaluasi.

    Uji ini gagal bila horizon kembali dibaca sebagai panjang rentang: pembacaan itu
    menempatkan jendela 6H pada H+1 sementara data menempatkannya pada H+0, dan
    menempatkan jendela 7D di sepanjang H+1..H+7 sementara data menempatkannya pada H+7
    saja. Inilah yang seharusnya menangkap kekeliruan itu sejak awal.
    """
    rows = session.scalars(select(Prediction)).all()
    assert rows, "tabel predictions kosong — jalankan seed lebih dahulu"

    seeded = [row for row in rows if row.model_version != engine.RULE_VERSION]
    assert seeded, "tidak ada prediksi seed untuk diuji — pembacaan horizon tidak terkunci"

    for row in rows:
        windows = engine.horizon_windows(row.prediction_date, row.forecast_horizon)
        assert (row.time_window, row.window_start, row.window_end) in windows, (
            f"{row.code} ({row.forecast_horizon}, dibuat {row.prediction_date}) menunjuk "
            f"jendela {row.window_start} yang tidak dihasilkan mesin ini"
        )


@pytestmark_db
def test_the_window_length_is_always_six_hours_in_the_database(session: Session) -> None:
    """Satu prediksi = satu bin 6 jam, berapa pun horizonnya — sifat data, bukan asumsi."""
    lengths = {
        row.window_end - row.window_start for row in session.scalars(select(Prediction)).all()
    }

    assert lengths == {timedelta(hours=6)}


@pytestmark_db
def test_running_requires_the_run_permission(client: TestClient, session: Session) -> None:
    """Pimpinan boleh membaca prediksi, tetapi tidak menjalankannya."""
    headers = _auth(client, _user(session, "Pimpinan"))
    status_code, _ = _run(client, headers)

    assert status_code == 403


@pytestmark_db
def test_a_denied_run_leaves_a_trace(client: TestClient, session: Session) -> None:
    """Penolakan otorisasi ikut tercatat — justru itulah bukti RBAC bekerja."""
    user = _user(session, "Pimpinan")
    headers = _auth(client, user)
    _run(client, headers)

    denied = session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.user_id == user.user_id, AuditLog.result == "DENIED")
    )
    assert (denied or 0) >= 1


@pytestmark_db
def test_dry_run_writes_nothing(client: TestClient, session: Session) -> None:
    headers = _auth(client, _user(session, "Administrator"))
    before = session.scalar(select(func.count()).select_from(Prediction)) or 0

    status_code, body = _run(client, headers, dry_run=True)

    assert status_code == 200, body
    assert body["dry_run"] is True
    assert body["written"] == 0
    assert (session.scalar(select(func.count()).select_from(Prediction)) or 0) == before
    assert int(body["predicted"]) > 0


@pytestmark_db
def test_the_response_never_claims_a_trained_model(client: TestClient, session: Session) -> None:
    """Versi yang dibawa adalah versi ATURAN, dan responsnya menyatakannya sendiri."""
    headers = _auth(client, _user(session, "Administrator"))
    _status, body = _run(client, headers)

    assert body["rule_version"] == engine.RULE_VERSION
    assert "BUKAN model terlatih" in str(body["projection_basis"])
    assert "Tidak ada model terlatih" in str(body["model_disclaimer"])
    for row in body["sample"]:
        for factor in row["dominant_factors"]:
            assert factor["source"] == "RULE"


@pytestmark_db
def test_each_sample_row_can_be_traced_back_to_its_baseline(
    client: TestClient, session: Session
) -> None:
    """Skor prediksi sama dengan skor penilaian yang menjadi dasarnya, dan barisnya disebut."""
    headers = _auth(client, _user(session, "Administrator"))
    _status, body = _run(client, headers)

    rows = list(body["sample"])
    assert rows

    for row in rows:
        baseline = session.scalar(select(RiskScore).where(RiskScore.code == row["baseline_code"]))
        assert baseline is not None
        assert baseline.risk_score == row["risk_score"]
        assert baseline.assessment_date.isoformat() == row["baseline_assessment_date"]
        # Prediksi menunjuk ke depan: penilaian dasarnya tidak boleh berasal dari masa
        # sesudah jendela yang diprediksi.
        assert int(row["baseline_age_days"]) >= 0


@pytestmark_db
def test_a_run_records_its_threshold_version_but_classifies_nothing(
    client: TestClient, session: Session
) -> None:
    """Versi ambang tetap dicatat, tetapi tidak dipakai memberi kelas pada prediksi.

    Sampai 9 September 2026 test ini justru MENUNTUT setiap baris contoh berkelas
    `thresholds.class_for(skor)`. Pemilik proyek kemudian memutuskan prediksi tetap skor
    mentah, sehingga tuntutan itu menjadi kebalikan dari yang harus dijaga.

    Versinya tetap dicatat karena ambang itulah yang menentukan apakah sebuah prediksi
    kelak melahirkan peringatan — hubungan yang harus tetap dapat ditelusuri.
    """
    headers = _auth(client, _user(session, "Administrator"))
    _status, body = _run(client, headers)
    thresholds = risk.load_thresholds()

    assert body["threshold_version"] == thresholds.version
    for row in body["sample"]:
        assert "risk_class" not in row, "prediksi tidak boleh diberi kelas"
        assert 0 <= int(row["risk_score"]) <= 100


@pytestmark_db
def test_every_sample_row_carries_a_confidence_reason(client: TestClient, session: Session) -> None:
    """Angka confidence tidak pernah tampil tanpa dasarnya."""
    headers = _auth(client, _user(session, "Administrator"))
    _status, body = _run(client, headers)

    for row in body["sample"]:
        assert 0 <= int(row["confidence"]) <= 100
        assert row["confidence_reason"]
        assert str(row["supporting_incidents"]) in str(row["confidence_reason"])


@pytestmark_db
def test_a_combination_without_a_baseline_is_reported_not_guessed(
    client: TestClient, session: Session
) -> None:
    """Yang tidak dapat diproyeksikan dihitung terpisah beserta alasannya."""
    headers = _auth(client, _user(session, "Administrator"))
    _status, body = _run(client, headers)

    assert int(body["combinations"]) == int(body["predicted"]) + int(body["not_predicted"])
    if int(body["not_predicted"]) > 0:
        assert body["not_predicted_reasons"]
        assert "risk_scores" in str(body["not_predicted_reasons"][0]["reason"])


@pytestmark_db
def test_writing_stores_drafts_that_point_at_their_baseline(
    client: TestClient, session: Session
) -> None:
    """Prediksi baru berstatus DRAFT dan membawa penelusuran ke penilaian dasarnya."""
    headers = _auth(client, _user(session, "Administrator"))
    status_code, body = _run(client, headers, dry_run=False)

    assert status_code == 200, body
    assert int(body["written"]) > 0
    assert body["status_written"] == engine.STATUS_DRAFT

    stored = session.scalars(
        select(Prediction).where(Prediction.prediction_date == date(2099, 1, 1))
    ).all()
    assert len(stored) == int(body["written"])

    for prediction in stored:
        assert prediction.status == engine.STATUS_DRAFT
        assert prediction.model_version == engine.RULE_VERSION
        assert prediction.baseline_risk_score_id is not None
        assert prediction.forecast_horizon == SHORT_HORIZON
        # 6H berjarak 0 hari, sehingga hari sasarannya adalah tanggal prediksi itu sendiri.
        assert prediction.window_start >= datetime(2099, 1, 1, tzinfo=clock.JAKARTA)
        assert prediction.window_end - prediction.window_start == timedelta(hours=6)


@pytestmark_db
def test_an_existing_date_and_horizon_is_never_overwritten(
    client: TestClient, session: Session
) -> None:
    """Prediksi adalah pernyataan bertanggal; menimpanya merusak dasar evaluasi."""
    headers = _auth(client, _user(session, "Administrator"))
    first, _ = _run(client, headers, dry_run=False)
    assert first == 200

    second, body = _run(client, headers, dry_run=False)

    assert second == 409, body
    assert "sudah memiliki" in str(body["error"]["message"])


@pytestmark_db
def test_an_unknown_horizon_is_refused_by_the_endpoint(
    client: TestClient, session: Session
) -> None:
    headers = _auth(client, _user(session, "Administrator"))
    status_code, body = _run(client, headers, horizon="48H")

    assert status_code == 422, body


@pytestmark_db
def test_running_is_recorded_in_the_audit_trail(client: TestClient, session: Session) -> None:
    """Uji coba pun tercatat: yang tidak ditulis adalah barisnya, bukan jejaknya."""
    user = _user(session, "Administrator")
    headers = _auth(client, user)
    _run(client, headers, dry_run=True)

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == user.user_id, AuditLog.action == "RUN_PREDICTION")
        .order_by(AuditLog.timestamp.desc())
    )
    assert entry is not None
    assert entry.resource_type == "prediction"
    assert entry.detail is not None
    assert entry.detail["dry_run"] is True


# ---------------------------------------------------------------------------
# Publikasi
# ---------------------------------------------------------------------------


def _draft(session: Session) -> Prediction:
    """Satu prediksi DRAFT milik test ini sendiri, agar hasilnya tidak bergantung seed."""
    location = session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None

    prediction = Prediction(
        code=f"PRD-UJI-{uuid.uuid4().hex[:6]}",
        prediction_date=date(2099, 1, 1),
        forecast_horizon=SHORT_HORIZON,
        threat_type="CURANMOR",
        location_id=location.location_id,
        time_window="00:00-06:00",
        window_start=datetime(2099, 1, 2, 0, 0, tzinfo=clock.JAKARTA),
        window_end=datetime(2099, 1, 2, 6, 0, tzinfo=clock.JAKARTA),
        risk_score=71,
        confidence=25,
        dominant_factors=[{"factor": "historical_factor", "contribution": 18.0, "source": "RULE"}],
        model_version=engine.RULE_VERSION,
        status=engine.STATUS_DRAFT,
    )
    session.add(prediction)
    session.flush()
    return prediction


@pytestmark_db
def test_publishing_requires_the_publish_permission(client: TestClient, session: Session) -> None:
    """Pimpinan tidak memegang `prediction:publish`; penolakannya terjadi di backend."""
    draft = _draft(session)
    headers = _auth(client, _user(session, "Pimpinan"))

    response = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)

    assert response.status_code == 403, response.text
    session.refresh(draft)
    assert draft.status == engine.STATUS_DRAFT


@pytestmark_db
def test_publishing_moves_a_draft_to_published(client: TestClient, session: Session) -> None:
    draft = _draft(session)
    headers = _auth(client, _user(session, "Administrator"))

    response = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == engine.STATUS_PUBLISHED
    session.refresh(draft)
    assert draft.status == engine.STATUS_PUBLISHED


@pytestmark_db
def test_a_published_prediction_is_not_published_again(
    client: TestClient, session: Session
) -> None:
    """Menerbitkan ulang akan mengaburkan urutan waktu yang menjadi dasar evaluasi."""
    draft = _draft(session)
    headers = _auth(client, _user(session, "Administrator"))

    first = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)
    assert first.status_code == 200, first.text
    repeat = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)

    assert repeat.status_code == 409, repeat.text
    assert engine.STATUS_DRAFT in repeat.json()["error"]["details"][0]["issue"]


@pytestmark_db
def test_publishing_an_unknown_code_is_a_not_found(client: TestClient, session: Session) -> None:
    headers = _auth(client, _user(session, "Administrator"))

    response = client.post("/api/v1/predictions/PRD-TIDAK-ADA/publish", headers=headers)

    assert response.status_code == 404, response.text


@pytestmark_db
def test_publishing_is_recorded_in_the_audit_trail(client: TestClient, session: Session) -> None:
    draft = _draft(session)
    user = _user(session, "Administrator")
    headers = _auth(client, user)

    client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == user.user_id, AuditLog.action == "PUBLISH_PREDICTION")
        .order_by(AuditLog.timestamp.desc())
    )
    assert entry is not None
    assert entry.resource_id == draft.code
    assert entry.detail is not None
    assert entry.detail["status_after"] == engine.STATUS_PUBLISHED
