"""Notifikasi — antrean pekerjaan pengguna, bukan kabar berita (TASK 164).

Permintaan pemilik proyek, 4 September 2026: penanda di pojok kanan atas yang isinya
**sesuai fungsi masing-masing peran**.

## Satu aturan yang menentukan seluruh modul ini

**Notifikasi adalah hal yang menunggu Anda kerjakan — bukan hal yang terjadi.**

Bedanya menentukan. Umpan "apa yang terjadi" akan sama bagi semua orang, terisi terus, dan
setelah dua hari tidak dibaca siapa pun; setiap orang belajar bahwa lencananya selalu merah
dan berhenti melihatnya. Antrean pekerjaan tidak begitu: ia menjadi nol ketika pekerjaannya
selesai, dan angka nol itulah yang membuat angka bukan-nol berarti sesuatu.

Karena itu tiap sumber di bawah diikat ke **permission tindakan**, bukan permission baca.
Seorang Pimpinan tidak diberi tahu ada laporan warga belum diverifikasi — ia tidak dapat
memverifikasinya, dan memberitahunya hanya menambah kecemasan tanpa jalan keluar. Sebaliknya
petugas Polsek tidak diberi tahu ada rekomendasi menunggu keputusan, sebab yang memutuskan
bukan dia.

Hasilnya berbeda-beda menurut peran, dan itu memang yang diminta:

```text
Pimpinan       rekomendasi menunggu keputusan
Polsek         peringatan belum diterima · laporan warga belum diverifikasi
Fungsi         (tidak ada antrean; kewenangannya menulis kejadian dan patroli)
Administrator  peringatan · laporan warga · prediksi draf · keputusan belum ditindaklanjuti
```

## Yang sengaja TIDAK dikerjakan di sini

Tidak ada penyimpanan "sudah dibaca". Notifikasi di sini **dihitung ulang dari keadaan
sebenarnya** setiap kali diminta, sehingga tidak mungkin menunjukkan pekerjaan yang sudah
selesai — dan tidak ada jalan bagi seseorang untuk menghilangkan pekerjaannya sendiri dari
daftar dengan menandainya terbaca. Penanda terbaca adalah kenyamanan yang, pada antrean
tugas, berubah menjadi cara melupakan tugas.

Seluruh sumber dibatasi cakupan wilayah di query, sama seperti layar lain.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import (
    CitizenReport,
    CommanderDecision,
    EarlyWarning,
    Location,
    OperationalAction,
    Prediction,
    Recommendation,
)
from ...services import clock
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission

router = APIRouter(tags=["notifikasi"])

#: Banyaknya butir contoh yang dibawa tiap sumber. Daftar yang lebih panjang berhenti
#: menjadi pengingat dan berubah menjadi layar daftar — yang memang sudah ada menunya.
SAMPLE_LIMIT = 3

NOTIFICATION_BASIS = (
    "Notifikasi di sini adalah pekerjaan yang MENUNGGU ANDA, bukan kabar tentang apa yang "
    "terjadi. Tiap sumber diikat ke permission tindakan, bukan permission baca: yang tidak "
    "dapat Anda kerjakan tidak ditampilkan, karena angka yang tidak dapat Anda selesaikan "
    "hanya menjadi kecemasan tanpa jalan keluar. Jumlahnya dihitung ulang dari keadaan "
    "sebenarnya setiap kali dibuka — tidak ada penanda 'sudah dibaca', sebab pada antrean "
    "tugas penanda seperti itu berubah menjadi cara melupakan tugas."
)


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


def _holds(current: CurrentUser, permission: str) -> bool:
    """Benar bila pengguna memegang permission tersebut."""
    return current.permissions.allows(permission)


@router.get("/notifications", summary="Antrean pekerjaan yang menunggu pengguna")
def notifications(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    """Pekerjaan yang menunggu pengguna ini, menurut apa yang dapat ia kerjakan.

    `dashboard:read` dipakai sebagai gerbang karena setiap peran memilikinya — gerbangnya
    bukan yang menentukan isi. Yang menentukan adalah permission tindakan yang diperiksa
    per sumber di bawah, dan itulah sebabnya dua peran yang sama-sama lolos gerbang ini
    tetap menerima daftar yang berbeda.
    """
    groups: list[dict[str, Any]] = []

    # --- Peringatan yang belum diterima siapa pun -------------------------------------
    if _holds(current, "warning:acknowledge"):
        polsek = jurisdiction_filter(current, "warning:read")
        rows = session.execute(
            _scoped(
                select(EarlyWarning, Location.kecamatan)
                .join(Location, Location.location_id == EarlyWarning.location_id)
                .where(EarlyWarning.status == "ACTIVE")
                .order_by(EarlyWarning.risk_score.desc()),
                polsek,
            ).limit(SAMPLE_LIMIT)
        ).all()
        total = session.scalar(
            _scoped(
                select(func.count())
                .select_from(EarlyWarning)
                .join(Location, Location.location_id == EarlyWarning.location_id)
                .where(EarlyWarning.status == "ACTIVE"),
                polsek,
            )
        )
        groups.append(
            {
                "kind": "WARNING",
                "title": "Peringatan belum diterima",
                "action": "Terima atau selesaikan",
                "href": "/peringatan",
                "total": int(total or 0),
                "items": [
                    {
                        "code": warning.code,
                        "headline": f"{warning.severity} — {warning.threat_type}",
                        "detail": f"{kecamatan} · skor {warning.risk_score}",
                    }
                    for warning, kecamatan in rows
                ],
            }
        )

    # --- Rekomendasi yang menunggu keputusan komandan ---------------------------------
    if _holds(current, "commander_decision:approve"):
        polsek = jurisdiction_filter(current, "recommendation:read")
        rows = session.execute(
            _scoped(
                select(Recommendation, Location.kecamatan)
                .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
                .join(Location, Location.location_id == Prediction.location_id)
                .where(Recommendation.status == "PENDING_REVIEW")
                .order_by(Prediction.risk_score.desc()),
                polsek,
            ).limit(SAMPLE_LIMIT)
        ).all()
        total = session.scalar(
            _scoped(
                select(func.count())
                .select_from(Recommendation)
                .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
                .join(Location, Location.location_id == Prediction.location_id)
                .where(Recommendation.status == "PENDING_REVIEW"),
                polsek,
            )
        )
        groups.append(
            {
                "kind": "DECISION",
                "title": "Menunggu keputusan Anda",
                "action": "Setujui, modifikasi, atau tolak",
                "href": "/rekomendasi",
                "total": int(total or 0),
                "items": [
                    {
                        "code": recommendation.code,
                        "headline": f"Untuk {recommendation.recommended_function}",
                        "detail": f"{kecamatan} · {recommendation.recommendation_text[:70]}",
                    }
                    for recommendation, kecamatan in rows
                ],
            }
        )

    # --- Laporan masyarakat yang belum diverifikasi -----------------------------------
    if _holds(current, "citizen_report:write"):
        polsek = jurisdiction_filter(current, "citizen_report:write")
        # Laporan tanpa lokasi tidak dapat dibebankan ke wilayah mana pun; pengguna
        # ber-cakupan tidak menerimanya, sebab menampilkannya berarti menebak.
        query = select(CitizenReport).where(CitizenReport.status == "RECEIVED")
        counter = (
            select(func.count())
            .select_from(CitizenReport)
            .where(CitizenReport.status == "RECEIVED")
        )
        if polsek is not None:
            query = query.join(Location, Location.location_id == CitizenReport.location_id).where(
                Location.polsek == polsek
            )
            counter = counter.join(
                Location, Location.location_id == CitizenReport.location_id
            ).where(Location.polsek == polsek)

        reports = session.scalars(
            query.order_by(CitizenReport.reported_at.desc()).limit(SAMPLE_LIMIT)
        ).all()
        groups.append(
            {
                "kind": "CITIZEN_REPORT",
                "title": "Laporan warga belum diverifikasi",
                "action": "Triase",
                "href": "/masyarakat?status=RECEIVED",
                "total": int(session.scalar(counter) or 0),
                "items": [
                    {
                        "code": report.code,
                        "headline": report.category,
                        "detail": (report.description or "")[:70] or "Tanpa keterangan.",
                    }
                    for report in reports
                ],
            }
        )

    # --- Prediksi yang belum dipublikasikan -------------------------------------------
    if _holds(current, "prediction:publish"):
        polsek = jurisdiction_filter(current, "prediction:read")
        total = session.scalar(
            _scoped(
                select(func.count())
                .select_from(Prediction)
                .join(Location, Location.location_id == Prediction.location_id)
                .where(Prediction.status == "DRAFT"),
                polsek,
            )
        )
        rows = session.execute(
            _scoped(
                select(Prediction, Location.kecamatan)
                .join(Location, Location.location_id == Prediction.location_id)
                .where(Prediction.status == "DRAFT")
                .order_by(Prediction.risk_score.desc()),
                polsek,
            ).limit(SAMPLE_LIMIT)
        ).all()
        groups.append(
            {
                "kind": "PREDICTION",
                "title": "Prediksi belum dipublikasikan",
                "action": "Tinjau lalu publikasikan",
                "href": "/prediksi",
                "total": int(total or 0),
                "items": [
                    {
                        "code": prediction.code,
                        "headline": prediction.threat_type,
                        "detail": f"{kecamatan} · skor {prediction.risk_score}",
                    }
                    for prediction, kecamatan in rows
                ],
            }
        )

    # --- Keputusan yang belum berubah menjadi tindakan --------------------------------
    if _holds(current, "operation:write"):
        polsek = jurisdiction_filter(current, "operation:read")
        pending = (
            select(CommanderDecision, Location.kecamatan)
            .join(
                Recommendation,
                Recommendation.recommendation_id == CommanderDecision.recommendation_id,
            )
            .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
            .join(Location, Location.location_id == Prediction.location_id)
            .where(
                CommanderDecision.decision.in_(("APPROVED", "MODIFIED")),
                ~select(OperationalAction.action_id)
                .where(OperationalAction.decision_id == CommanderDecision.decision_id)
                .exists(),
            )
        )
        rows = session.execute(
            _scoped(pending.order_by(CommanderDecision.decision_at.desc()), polsek).limit(
                SAMPLE_LIMIT
            )
        ).all()
        total = session.scalar(
            select(func.count()).select_from(_scoped(pending, polsek).subquery())
        )
        groups.append(
            {
                "kind": "OPERATION",
                "title": "Keputusan belum ditindaklanjuti",
                "action": "Catat tindakan operasional",
                "href": "/operasi",
                "total": int(total or 0),
                "items": [
                    {
                        "code": decision.code,
                        "headline": f"Keputusan {decision.decision}",
                        "detail": f"{kecamatan} · belum ada tindakan tercatat",
                    }
                    for decision, kecamatan in rows
                ],
            }
        )

    # Kelompok kosong tetap dikembalikan, tidak dibuang: "0 peringatan menunggu" adalah
    # kabar baik yang pantas terbaca, dan menghilangkan barisnya membuat pengguna tidak
    # dapat membedakan "tidak ada" dari "tidak diperiksa".
    return {
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "role": current.permissions.role_name,
        "total": sum(int(group["total"]) for group in groups),
        "groups": groups,
        "basis": NOTIFICATION_BASIS,
    }
