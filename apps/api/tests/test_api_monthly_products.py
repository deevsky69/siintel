"""Modul 4 mekanisme, dua tahap (10 November 2026): draf membekukan peringkat → analis memeriksa
dan mengirim → Pimpinan menetapkan → pelaksanaan; alasan wajib dan kewenangan per peran (1B)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock, monthly_ranking

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
MONTH = "2032-03"
BASE = "/api/v1/monthly-products"


@pytest.fixture(autouse=True)
def _peta_tiga_bulan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dasar usulan dipatok ke peta 3 bulan: pilihan penjaga (model atau peta) bergantung
    pada isi basis data, sedangkan test ini memeriksa alur, bukan pemilihan metode."""
    monkeypatch.setattr(
        monthly_ranking,
        "operational",
        lambda *args, **kwargs: monthly_ranking.MethodChoice("HISTORY_3M", "uji", {}),
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


def _login(
    client: TestClient, session: Session, role_name: str, polsek: str | None = None
) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, role_name
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
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed(session: Session) -> Location:
    area = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.kelurahan)
    )
    assert area is not None
    for i in range(5):
        day = date(2032, 1, 4) + timedelta(days=i * 7)
        session.add(
            CrimeIncident(
                code=f"INC-UJI-{uuid.uuid4().hex[:8]}",
                incident_type="CURANMOR",
                occurred_at=datetime.combine(day, time(22, 0), tzinfo=clock.JAKARTA),
                incident_date=day,
                incident_time=time(22, 0),
                time_known=True,
                location_id=area.location_id,
                reported_at=datetime.combine(day, time(23, 0), tzinfo=clock.JAKARTA),
                vehicle_object=True,
                # Empat di kos, satu tanpa tempat tercatat → tempat terbanyak: kos.
                location_type="Kost" if i < 4 else None,
                status="REPORTED",
            )
        )
    session.flush()
    return area


def _post(client: TestClient, path: str, body: dict[str, Any], headers: dict[str, str]) -> Any:
    return client.post(f"{BASE}/{MONTH}/{path}", json=body, headers=headers)


def test_full_chain_from_draft_to_recorded_action(client: TestClient, session: Session) -> None:
    area = _seed(session)
    analyst = _login(client, session, "Analis Intelkam")
    kbo = _login(client, session, "KBO")
    wakasat = _login(client, session, "Wakasat Intelkam")
    kasat = _login(client, session, "Kasat Intelkam")
    leader = _login(client, session, "Pimpinan")
    polsek_in = _login(client, session, "Polsek", polsek=area.polsek)

    # Menyusun butuh `monthly_product:draft`: Analis Intelkam — bukan Pimpinan, Kasat, atau KBO.
    # (Administrator memegang seluruh kewenangan sejak 19 November 2026; lihat test di bawah.)
    assert client.post(BASE, json={"month": MONTH}, headers=leader).status_code == 403
    assert client.post(BASE, json={"month": MONTH}, headers=kasat).status_code == 403
    assert client.post(BASE, json={"month": MONTH}, headers=kbo).status_code == 403

    # "Susun" membekukan peringkat bulan itu sekaligus — tidak ada langkah terpisah.
    assert client.get(f"/api/v1/rankings?month={MONTH}", headers=analyst).json()["frozen"] is False
    created = client.post(BASE, json={"month": MONTH}, headers=analyst)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "DRAFT" and body["next_stage"] == "ANALYST"
    assert body["facts"]["ranking_frozen_by_draft"] is True
    assert client.get(f"/api/v1/rankings?month={MONTH}", headers=analyst).json()["frozen"] is True
    assert body["items"][0]["kelurahan"] == area.kelurahan
    assert body["items"][0]["pattern"]["dominant_threat"] == "CURANMOR"
    assert body["items"][0]["pattern"]["peak_block_label"] == "20.00-24.00"
    # Rentang jam per jenis, dengan jumlah laporan berjam dan tanpa jam (naskah Bab IV).
    first = body["items"][0]
    assert first["pattern"]["peaks_by_threat"]["CURANMOR"] == {
        "block_start": 20,
        "block_label": "20.00-24.00",
        "count": 5,
        "with_time": 5,
        "unknown_time": 0,
    }
    # Rekomendasi menurut tempat kejadian (naskah Tabel 13): kos → Binmas, pengelola.
    assert first["pattern"]["dominant_place"] == "kos" and first["pattern"]["places"] == {"kos": 4}
    assert first["proposed_function"] == "BINMAS"
    assert "pengelola atau pemilik" in first["proposal_text"]
    assert "4 dari 5 laporan" in first["proposal_text"]
    assert "Pelaksana: Binmas, Polsek" in first["proposal_text"]
    assert "5 dari 5 laporan berjam; 0 tanpa jam" in first["proposal_text"]
    # Kelurahan tanpa tempat tercatat memakai aturan per jenis ancaman, bukan mengarang tempat.
    plain = body["items"][-1]
    assert (
        plain["pattern"]["dominant_place"] is None
        and "Tempat terbanyak" not in plain["proposal_text"]
    )
    assert client.post(BASE, json={"month": MONTH}, headers=analyst).status_code == 409
    # Kasat belum dapat menelaah draf yang belum dikirim staf.
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat).status_code == 409

    # Staf: tolak tanpa alasan ditolak; dengan alasan diterima → menunggu telaah Kasat.
    second = body["items"][1]["kelurahan"]
    bad = _post(
        client, "analyst", {"items": [{"kelurahan": second, "status": "REJECTED"}]}, analyst
    )
    assert bad.status_code == 400
    assert (
        _post(client, "decide", {"selected": [{"kelurahan": area.kelurahan}]}, leader).status_code
        == 409
    )
    reviewed = _post(
        client,
        "analyst",
        {
            "items": [
                {
                    "kelurahan": area.kelurahan,
                    "status": "REVISED",
                    "text": "Koordinasi pengelola parkir",
                    "reason": "laporan Babin: parkir liar",
                },
                {"kelurahan": second, "status": "REJECTED", "reason": "tidak didukung lapangan"},
            ],
            "note": "diperiksa 10 Nov",
        },
        analyst,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "ANALYST_REVIEWED"
    assert reviewed.json()["next_stage"] == "KBO"
    assert reviewed.json()["awaiting_kbo"] is True
    assert reviewed.json()["awaiting_review"] is False
    assert reviewed.json()["awaiting_decision"] is False
    assert reviewed.json()["items"][1]["analyst_status"] == "REJECTED"

    # Lima pemeriksa (21 November 2026, naskah Taskap revisi): KBO memeriksa mutu, lalu Wakasat,
    # baru Kasat menelaah. Kasat dan Wakasat belum dapat bertindak, dan hanya KBO yang memeriksa
    # di tahap ini — bukan analis yang menulisnya.
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat).status_code == 409
    assert _post(client, "wakasat", {"outcome": "ACCEPTED"}, wakasat).status_code == 409
    for other_role in (analyst, wakasat, kasat, leader):
        assert _post(client, "kbo", {"outcome": "ACCEPTED"}, other_role).status_code == 403
    assert _post(client, "kbo", {"outcome": "REJECTED"}, kbo).status_code == 400
    checked = _post(client, "kbo", {"outcome": "ACCEPTED"}, kbo)
    assert checked.status_code == 200, checked.text
    assert checked.json()["status"] == "KBO_CHECKED" and checked.json()["next_stage"] == "WAKASAT"
    assert checked.json()["awaiting_wakasat"] is True
    assert checked.json()["awaiting_review"] is False

    # Wakasat memeriksa sesudah KBO: Kasat belum dapat menelaah, peran lain ditolak, pengembalian
    # tanpa alasan ditolak.
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat).status_code == 409
    for other_role in (analyst, kbo, kasat, leader):
        assert _post(client, "wakasat", {"outcome": "ACCEPTED"}, other_role).status_code == 403
    assert _post(client, "wakasat", {"outcome": "REJECTED"}, wakasat).status_code == 400
    examined = _post(client, "wakasat", {"outcome": "ACCEPTED"}, wakasat)
    assert examined.status_code == 200, examined.text
    assert examined.json()["status"] == "WAKASAT_CHECKED"
    assert examined.json()["next_stage"] == "KASAT"
    assert examined.json()["awaiting_wakasat"] is False
    assert examined.json()["awaiting_review"] is True

    pick = {"selected": [{"kelurahan": area.kelurahan}]}
    # Pimpinan belum dapat menetapkan sebelum Kasat menelaah.
    assert _post(client, "decide", pick, leader).status_code == 409
    # Telaah hanya oleh Kasat Intelkam — bukan staf yang menulisnya, bukan KBO, bukan Pimpinan.
    for other_role in (analyst, kbo, wakasat, leader):
        assert _post(client, "kasat", {"outcome": "ACCEPTED"}, other_role).status_code == 403
    # Mengembalikan tanpa alasan ditolak; dengan alasan produk kembali menjadi draf staf.
    assert _post(client, "kasat", {"outcome": "REJECTED"}, kasat).status_code == 400
    assert _post(client, "kasat", {"outcome": "SETUJU"}, kasat).status_code == 400
    returned = _post(
        client, "kasat", {"outcome": "REJECTED", "reason": "lengkapi dasar lapangan"}, kasat
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "DRAFT" and returned.json()["next_stage"] == "ANALYST"
    assert _post(client, "decide", pick, leader).status_code == 409
    # Staf mengirim ulang; pemeriksaan sebelumnya tetap tersimpan.
    resent = _post(client, "analyst", {"items": [], "note": "dasar dilengkapi"}, analyst)
    assert resent.status_code == 200, resent.text
    assert resent.json()["items"][1]["analyst_status"] == "REJECTED"
    # Setelah dikembalikan, produk melewati KBO dan Wakasat lagi sebelum sampai ke Kasat.
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat).status_code == 409
    assert _post(client, "kbo", {"outcome": "ACCEPTED"}, kbo).status_code == 200
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat).status_code == 409
    assert _post(client, "wakasat", {"outcome": "ACCEPTED"}, wakasat).status_code == 200
    passed = _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat)
    assert passed.status_code == 200, passed.text
    assert passed.json()["status"] == "VALIDATED" and passed.json()["next_stage"] == "PIMPINAN"
    assert passed.json()["awaiting_decision"] is True
    # Kasat menelaah, tidak menetapkan.
    assert _post(client, "decide", pick, kasat).status_code == 403

    # Pimpinan menetapkan: yang ditolak staf tidak dapat dipilih; KBO dan staf tidak boleh.
    assert _post(client, "decide", pick, kbo).status_code == 403
    assert _post(client, "decide", pick, analyst).status_code == 403
    assert _post(client, "decide", {"selected": [{"kelurahan": second}]}, leader).status_code == 400
    decided = _post(
        client,
        "decide",
        {
            "selected": [{"kelurahan": area.kelurahan, "action": "Patroli malam dan parkir"}],
            "reason": "sumber daya tersedia",
        },
        leader,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "DECIDED" and decided.json()["priority_count"] == 1
    chosen = decided.json()["items"][0]
    assert chosen["selected"] is True and chosen["decided_action"].startswith("Patroli")
    stages = [s["stage"] for s in decided.json()["stages"]]
    assert stages == [
        "ANALYST", "KBO", "WAKASAT", "KASAT",
        "ANALYST", "KBO", "WAKASAT", "KASAT", "PIMPINAN",
    ]  # fmt: skip

    # Pelaksanaan: Polsek wilayah mencatat; Polsek lain 404; bukan prioritas 404.
    action = {
        "acted_at": "2032-03-05T21:00:00+07:00",
        "place": "Parkiran pasar",
        "action": "Patroli dan penjagaan",
        "result": "aman",
    }
    other = _login(client, session, "Polsek", polsek="Polsek Lain Uji")
    path = f"items/{area.kelurahan}/actions"
    assert _post(client, path, action, other).status_code == 404
    assert _post(client, f"items/{second}/actions", action, polsek_in).status_code == 404
    recorded = _post(client, path, action, polsek_in)
    assert recorded.status_code == 201, recorded.text
    assert recorded.json()["unit"] == area.polsek

    final = client.get(f"{BASE}/{MONTH}", headers=leader).json()
    assert len(final["items"][0]["actions"]) == 1
    months = [row["target_month"] for row in client.get(BASE, headers=leader).json()["data"]]
    assert MONTH in months


def test_administrator_can_run_every_stage_of_the_chain(
    client: TestClient, session: Session
) -> None:
    """Keputusan pemilik proyek 19 November 2026 (catatan 187): seluruh kewenangan peran lain
    dapat dijalankan Administrator — termasuk tiap tahap rantai produk bulanan.

    Urutan tahap TETAP ditegakkan (tidak ada tahap yang dapat dilompati), dan tiap tahap
    mencatat akun pelakunya; yang hilang hanyalah keharusan empat peran berbeda."""
    area = _seed(session)
    admin = _login(client, session, "Administrator")

    created = client.post(BASE, json={"month": MONTH}, headers=admin)
    assert created.status_code == 201, created.text
    pick = {"selected": [{"kelurahan": area.kelurahan}]}
    # Urutan tetap berlaku bagi Administrator: belum dapat menetapkan draf yang belum ditelaah.
    assert _post(client, "decide", pick, admin).status_code == 409
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, admin).status_code == 409

    reviewed = _post(client, "analyst", {"items": [], "note": "diperiksa admin"}, admin)
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "ANALYST_REVIEWED"
    assert _post(client, "kbo", {"outcome": "ACCEPTED"}, admin).json()["status"] == "KBO_CHECKED"
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, admin).status_code == 409
    examined = _post(client, "wakasat", {"outcome": "ACCEPTED"}, admin)
    assert examined.json()["status"] == "WAKASAT_CHECKED"
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, admin).json()["status"] == "VALIDATED"
    decided = _post(client, "decide", pick, admin)
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "DECIDED"
    stages = [s["stage"] for s in decided.json()["stages"]]
    assert stages == ["ANALYST", "KBO", "WAKASAT", "KASAT", "PIMPINAN"]

    action = {
        "acted_at": "2032-03-05T21:00:00+07:00",
        "place": "Parkiran pasar",
        "action": "Patroli dan penjagaan",
        "result": "aman",
    }
    recorded = _post(client, f"items/{area.kelurahan}/actions", action, admin)
    assert recorded.status_code == 201, recorded.text


def test_kbo_can_return_a_product_to_the_analyst(client: TestClient, session: Session) -> None:
    """KBO mengembalikan dengan alasan; produk kembali menjadi draf analis."""
    _seed(session)
    analyst = _login(client, session, "Analis Intelkam")
    kbo = _login(client, session, "KBO")
    assert client.post(BASE, json={"month": MONTH}, headers=analyst).status_code == 201
    # Draf yang belum dikirim analis belum dapat diperiksa KBO.
    assert _post(client, "kbo", {"outcome": "ACCEPTED"}, kbo).status_code == 409
    assert _post(client, "analyst", {"items": []}, analyst).status_code == 200
    returned = _post(
        client, "kbo", {"outcome": "REJECTED", "reason": "validasi belum lengkap"}, kbo
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "DRAFT" and returned.json()["next_stage"] == "ANALYST"
    last = returned.json()["stages"][-1]
    assert last["stage"] == "KBO" and last["reason"] == "validasi belum lengkap"


def test_kbo_records_draft_quality_and_work_times(client: TestClient, session: Session) -> None:
    """Modul 5 (naskah Taskap Tabel 4.17 dan Lampiran L huruf D): skor mutu draf menurut rubrik
    empat unsur dan cap waktu kerja dicatat KBO; "draf siap" dan "validasi selesai" diambil dari
    catatan sistem, bukan diisi tangan."""
    _seed(session)
    analyst = _login(client, session, "Analis Intelkam")
    kbo = _login(client, session, "KBO")
    wakasat = _login(client, session, "Wakasat Intelkam")
    kasat = _login(client, session, "Kasat Intelkam")
    assert client.post(BASE, json={"month": MONTH}, headers=analyst).status_code == 201

    full = {"traceability": 2, "place_time": 2, "field_fit": 1, "feasibility": 2}
    body = {
        "quality_sigap": full,
        "quality_manual": {"traceability": 1, "place_time": 1, "field_fit": 1, "feasibility": 2},
        "received_at": "2032-02-03T08:00:00+07:00",
        "data_ready_at": "2032-02-03T10:30:00+07:00",
        "map_ready_at": "2032-02-03T11:00:00+07:00",
        "note": "diperiksa terhadap rekap Polsek",
    }
    # Yang menulis draf tidak menilai mutunya sendiri; Kasat pun tidak.
    assert _post(client, "work-log", body, analyst).status_code == 403
    assert _post(client, "work-log", body, kasat).status_code == 403
    # Rubrik: keempat unsur wajib, tiap unsur 0–2; urutan waktu harus masuk akal.
    assert (
        _post(client, "work-log", {**body, "quality_sigap": {"traceability": 2}}, kbo).status_code
        == 400
    )
    assert (
        _post(
            client, "work-log", {**body, "quality_sigap": {**full, "feasibility": 3}}, kbo
        ).status_code
        == 400
    )
    late = {**body, "data_ready_at": "2032-02-03T07:00:00+07:00"}
    assert _post(client, "work-log", late, kbo).status_code == 400

    recorded = _post(client, "work-log", body, kbo)
    assert recorded.status_code == 200, recorded.text
    work = recorded.json()
    assert work["recorded"] is True
    assert work["quality_sigap_total"] == 7 and work["quality_manual_total"] == 5
    assert work["quality_max"] == 8 and len(work["rubric"]) == 4
    assert work["minutes_receive_to_ready"] == 150
    # Belum ditelaah Kasat: waktu sampai validasi belum dapat dihitung.
    assert work["validated_at"] is None and work["minutes_ready_to_validated"] is None
    assert work["draft_ready_at"] is not None

    assert _post(client, "analyst", {"items": []}, analyst).status_code == 200
    assert _post(client, "kbo", {"outcome": "ACCEPTED"}, kbo).status_code == 200
    assert _post(client, "wakasat", {"outcome": "ACCEPTED"}, wakasat).status_code == 200
    assert _post(client, "kasat", {"outcome": "ACCEPTED"}, kasat).status_code == 200
    evaluation = client.get(f"/api/v1/evaluation/monthly?month={MONTH}", headers=kbo)
    assert evaluation.status_code == 200, evaluation.text
    shown = evaluation.json()["work"]
    assert shown["quality_sigap_total"] == 7
    assert shown["validated_at"] is not None  # dari tahap KASAT, bukan isian
