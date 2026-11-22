"""Model prediksi bulanan (gradient boosting) dan penjaga pemakaiannya — hitungan murni,
tanpa basis data: batas informasi, pelatihan deterministik, alasan, uji tanda, PAI."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from prediksi_presisi_api.services import monthly_evaluation as evaluation
from prediksi_presisi_api.services import monthly_model as model
from prediksi_presisi_api.services import monthly_ranking as ranking

AREAS = {
    "Ramai": "Utara",
    "Sedang": "Utara",
    "Sepi": "Utara",
    "Naik": "Selatan",
    "Turun": "Selatan",
    "Kosong": "Selatan",
}
PARAMS = model.ModelParams(
    version="uji",
    train_until=date(2024, 12, 31),
    data_from=date(2023, 1, 1),
    max_iter=40,
    max_leaf_nodes=5,
    min_samples_leaf=5,
    learning_rate=0.1,
    min_training_rows=60,
)


def _monthly_count(name: str, index: int) -> int:
    step = index - model.month_index(date(2023, 1, 1))
    return {
        "Ramai": 8 + step % 3,
        "Sedang": 4 + step % 2,
        "Sepi": 1,
        "Naik": step // 4,
        "Turun": max(0, 9 - step // 4),
        "Kosong": 0,
    }[name]


def _history(until: date = date(2025, 12, 31)) -> model.IncidentHistory:
    incidents: list[tuple[str, date, date]] = []
    for index in range(model.month_index(date(2023, 1, 1)), model.month_index(until) + 1):
        first = model.month_from_index(index)
        for name in AREAS:
            for n in range(_monthly_count(name, index)):
                day = first + timedelta(days=n * 2)
                incidents.append((name, day, day + timedelta(days=1)))
    return model.IncidentHistory(incidents, AREAS, PARAMS.data_from)


def test_history_counts_only_what_was_reported_by_the_cutoff() -> None:
    late = (date(2024, 3, 30), date(2024, 4, 5))  # terjadi Maret, baru dilaporkan April
    history = model.IncidentHistory(
        [("Ramai", date(2024, 3, 2), date(2024, 3, 2)), ("Ramai", *late)], AREAS
    )
    march = model.month_index(date(2024, 3, 1))
    assert history.count("Ramai", march, date(2024, 3, 31)) == 1
    assert history.count("Ramai", march, date(2024, 4, 5)) == 2
    # Riwayat bulan sasaran April hanya memuat yang sudah diketahui sebelum April.
    features = dict(
        zip(model.FEATURES, history.features("Ramai", march + 1, date(2024, 3, 31)), strict=True)
    )
    assert features["mean_1"] == 1.0 and features["horizon"] == 1.0


def test_rows_before_data_from_are_ignored_and_windows_shorten() -> None:
    history = model.IncidentHistory(
        [
            ("Ramai", date(2021, 5, 1), date(2021, 5, 1)),
            ("Ramai", date(2023, 1, 9), date(2023, 1, 9)),
        ],
        AREAS,
        date(2023, 1, 1),
    )
    assert history.first_month == model.month_index(date(2023, 1, 1))
    february = model.month_index(date(2023, 2, 1))
    assert history.series("Ramai", february, date(2023, 1, 31)) == [1]


def test_training_is_deterministic_and_never_sees_the_test_period() -> None:
    history = _history()
    first = model.train(history, PARAMS)
    model._CACHE.clear()
    second = model.train(_history(), PARAMS)
    assert first.version == second.version and first.version.startswith("hgb-uji#")
    assert first.first_target == date(2023, 7, 1) and first.last_target == date(2024, 12, 1)
    # Naskah Lampiran 8 E: bulan sasaran Juli 2023–Desember 2024 dengan horizon 1–12 yang
    # tersedia → 150 pasangan (bulan, horizon) per kelurahan; pada 65 kelurahan = 9.750 baris.
    assert first.training_rows == len(AREAS) * 150
    rows, _, weights, targets = model.training_rows(history, PARAMS)
    july = [
        w for w, t in zip(weights, targets, strict=True) if t == model.month_index(date(2023, 7, 1))
    ]
    assert set(july) == {1.0}  # hanya horizon 1 yang tersedia
    december = [
        w
        for w, t in zip(weights, targets, strict=True)
        if t == model.month_index(date(2024, 12, 1))
    ]
    assert set(december) == {1 / 12} and len(rows) == len(weights)
    # Mengubah kejadian SETELAH masa latih tidak mengubah model.
    assert model.train(_history(date(2025, 6, 30)), PARAMS).version == first.version
    with pytest.raises(model.ModelUnavailable):
        model.predict_month(history, first, model.month_index(date(2024, 12, 1)))


def test_prediction_ranks_busy_areas_first_and_explains_itself() -> None:
    history = _history()
    trained = model.train(history, PARAMS)
    target = model.month_index(date(2025, 6, 1))
    predictions = {p.kelurahan: p for p in model.predict_month(history, trained, target)}
    assert predictions["Ramai"].predicted > predictions["Sedang"].predicted
    assert predictions["Sedang"].predicted > predictions["Kosong"].predicted
    for prediction in predictions.values():
        explained = prediction.base + sum(prediction.contributions.values())
        # Kontribusi berasal dari pohon model, pada skala logaritma (kerugian Poisson):
        # exp(nilai awal + jumlah kontribusi) tepat sama dengan perkiraan.
        assert math.exp(explained) == pytest.approx(prediction.predicted, rel=1e-6)
        # Kontribusi harus sebanding dengan perkiraannya sendiri: selisih log terhadap nilai
        # awal tidak mungkin jauh lebih kecil daripada kontribusi tunggal terbesar. (Cacat 19
        # November 2026: nilai simpul dalam yang tidak sebanding membengkakkan kontribusi
        # hingga ribuan persen tanpa mengubah jumlahnya.)
        assert max(abs(v) for v in prediction.contributions.values()) < 6
    spread = max(p.base for p in predictions.values()) - min(p.base for p in predictions.values())
    assert spread == pytest.approx(0.0, abs=1e-9)  # nilai awal sama untuk semua kelurahan
    # Skenario tetap: riwayat berhenti di akhir masa latih, horizon = jarak ke bulan sasaran.
    fixed = model.predict_month(history, trained, target, PARAMS.train_until, horizon=6)
    assert {p.features["horizon"] for p in fixed} == {6.0}
    with pytest.raises(model.ModelUnavailable):
        model.predict_month(history, trained, target, horizon=13)


def test_model_is_unavailable_without_enough_history() -> None:
    short = model.IncidentHistory([("Ramai", date(2024, 11, 3), date(2024, 11, 3))], AREAS)
    with pytest.raises(model.ModelUnavailable):
        model.train(short, PARAMS)


def test_sign_test_and_pai() -> None:
    assert evaluation.sign_test(0, 0) is None
    assert evaluation.sign_test(5, 5) == pytest.approx(0.623, abs=1e-3)
    assert evaluation.sign_test(12, 0) == pytest.approx(0.0002, abs=1e-4)
    assert evaluation.sign_test(10, 2) == pytest.approx(0.0193, abs=1e-4)
    assert evaluation.pai(30, 100, 0.10) == 3.0
    assert evaluation.pai(30, 0, 0.10) is None and evaluation.pai(30, 100, None) is None


def test_area_file_holds_the_bps_areas_of_the_manuscript() -> None:
    """Naskah revisi 7 Lampiran J bagian M: 28 kelurahan berluas BPS, wilayah hukum 144,75 km²."""
    from prediksi_presisi_api.services import kelurahan_area

    areas = evaluation.kelurahan_areas()
    assert len(areas) == 28 and all(value > 0 for value in areas.values())
    assert kelurahan_area.total_km2() == 144.75
    assert areas["Cipete Utara"] == 1.83 and areas["Pondok Pinang"] == 6.84
    assert areas["Rawa Barat"] == 0.69 and areas["Srengseng Sawah"] == 6.75
    # Januari 2025 pada naskah: enam kelurahan pilihan AI.
    chosen = ["Cipete Utara", "Gandaria Utara", "Cilandak Barat", "Kalibata", "Pulo", "Senayan"]
    share = kelurahan_area.share(chosen)
    assert share == pytest.approx((1.83 + 1.52 + 6.08 + 2.29 + 1.27 + 1.53) / 144.75)
    # Kelurahan tanpa luas pada naskah, atau angka sebatas satu Polsek: PAI tidak dihitung.
    assert kelurahan_area.share([*chosen[:5], "Karet Kuningan"]) is None
    assert kelurahan_area.share(chosen, whole_jurisdiction=False) is None
    assert kelurahan_area.share([]) is None


def test_random_baseline_matches_the_manuscript() -> None:
    """Lampiran J bagian M: acak 6 dari 65 = 9,23%; 58,5 dari 634 dan 44,6 dari 483."""
    assert evaluation.random_baseline(6, 65, 634) == {
        "top_n": 6,
        "kelurahan_total": 65,
        "coverage_pct": 9.23,
        "expected_covered": 58.5,
    }
    assert evaluation.random_baseline(6, 65, 483)["expected_covered"] == 44.6
    # Kelipatan terhadap acak: 29,97% → 3,25×; 17,81% → 1,93×; 16,36% → 1,77×.
    assert evaluation.vs_random(29.97, 6, 65) == 3.25
    assert evaluation.vs_random(27.76, 6, 65) == 3.01
    assert evaluation.vs_random(17.81, 6, 65) == 1.93
    assert evaluation.vs_random(16.36, 6, 65) == 1.77
    assert evaluation.vs_random(None, 6, 65) is None


def test_guard_falls_back_until_the_model_is_tested_and_reports_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ranking.load_config()
    assert config.kind(config.default_method) == "model"
    history = _history()
    monkeypatch.setattr(model, "train", lambda h, _params: model_train(h, PARAMS))
    # Bulan sasaran tepat setelah masa latih: belum ada bulan uji → peta historis.
    early = ranking.operational(None, date(2025, 2, 1), "VEHICLE", history)  # type: ignore[arg-type]
    assert early.method == config.guard_fallback and "belum dapat dinilai" in early.reason

    later = ranking.operational(None, date(2026, 1, 1), "VEHICLE", history)  # type: ignore[arg-type]
    covered = later.evidence["covered"]
    assert set(covered) == set(config.methods)
    best = max(v for k, v in covered.items() if k != "MODEL")
    # Naskah revisi 7 sasaran 3.3.1: tiga siklus; selisih cakupan sekurang-kurangnya 1 poin
    # persen DAN PAI sekurang-kurangnya 2,0 — selain itu peringkat historis terbaik.
    assert len(later.evidence["months"]) == 3
    assert (config.guard_months, config.guard_min_margin_pct, config.guard_min_pai) == (3, 1.0, 2.0)
    total = later.evidence["actual_total"]
    margin = later.evidence["margin_pct"]
    assert margin == pytest.approx((covered["MODEL"] - best) / total * 100, abs=0.01)
    pai = later.evidence["model_pai"]
    met = margin >= 1.0 and pai is not None and pai >= 2.0
    assert later.evidence["met"] is met and (later.method == "MODEL") is met
    assert ("Memenuhi ambang" in later.reason) is met
    assert ("peringkat historis terbaik dipakai" in later.reason) is not met


model_train = model.train


# --- IKW (naskah Taskap final Bab IV B.4.2 dan Lampiran 9) --------------------------------

IKW_CONFIG = ranking.load_config().ikw


def test_ikw_matches_the_worked_example_in_the_manuscript() -> None:
    from prediksi_presisi_api.services import ikw

    # Lampiran 9 E: 24 kejadian, kuartil 6/13/28 → F = 3; kehilangan tanpa cedera → D = 2;
    # empat dari empat bulan → T = 4. IKW = 25 × (0,50·3 + 0,35·2 + 0,15·4) = 70, tinggi.
    bounds = (6.0, 13.0, 28.0)
    assert ikw.frequency_score(24, bounds) == 3
    assert ikw.impact_score("PRESENT", "NONE") == 2
    result = ikw.compute(24, bounds, 4, [2], IKW_CONFIG)
    assert result["value"] == 70.0 and result["category"] == "TINGGI"
    assert result["status"] == ikw.STATUS_COMPLETE and result["review_now"] is False
    # Konfirmasi cedera berat menaikkan D menjadi 4 dan skor menjadi 87,5 — telaah segera.
    severe = ikw.compute(24, bounds, 4, [2, ikw.impact_score("PRESENT", "SEVERE")], IKW_CONFIG)
    assert severe["value"] == 87.5 and severe["review_now"] is True


def test_ikw_scores_and_status_follow_impact_verification() -> None:
    from prediksi_presisi_api.services import ikw

    assert ikw.impact_score("NONE", "NONE") == 1
    assert ikw.impact_score("UNKNOWN", "INJURY") == 3
    assert ikw.impact_score("PRESENT", "DEATH") == 4
    assert ikw.impact_score("UNKNOWN", "NONE") is None  # belum cukup untuk dinilai
    bounds = ikw.frequency_bounds([0, 0, 2, 4, 6, 8, 10])
    assert bounds == (4.0, 6.0, 8.0)
    assert [ikw.frequency_score(v, bounds) for v in (0, 2, 4, 5, 8, 10)] == [0, 1, 1, 2, 3, 4]
    assert ikw.frequency_bounds([0, 0]) is None and ikw.frequency_score(0, None) == 0

    # Tanpa laporan pada jendela dampak: lengkap, D = 0.
    quiet = ikw.compute(5, bounds, 0, [], IKW_CONFIG)
    assert quiet["status"] == ikw.STATUS_COMPLETE and quiet["impact"] == 0
    assert quiet["value"] == 25 * 0.5 * 2 and quiet["category"] == "RENDAH"
    # Sebagian terverifikasi: sementara, D dari yang sudah terverifikasi.
    partial = ikw.compute(10, bounds, 3, [2, None, None], IKW_CONFIG)
    assert partial["status"] == ikw.STATUS_PROVISIONAL and partial["impact"] == 2
    assert partial["impact_verified"] == 1 and partial["impact_reports"] == 3
    # Belum satu pun terverifikasi: ditahan — IKW tidak diterbitkan, bukan dianggap nol.
    held = ikw.compute(10, bounds, 3, [None, None], IKW_CONFIG)
    assert held["status"] == ikw.STATUS_WITHHELD and held["value"] is None
    assert held["category"] is None and held["frequency"] == 4
    # Batas kategori: sedang mulai 35, tinggi mulai 65.
    assert IKW_CONFIG.category(34.9) == "RENDAH" and IKW_CONFIG.category(35) == "SEDANG"
    assert IKW_CONFIG.category(64.9) == "SEDANG" and IKW_CONFIG.category(65) == "TINGGI"
