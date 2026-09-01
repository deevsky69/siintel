"""Executive Brief harian untuk pimpinan (modul MVP #14).

Spesifikasi menyebut modul ini tiga kali — §3, §8 keluaran no. 8, dan §9 MVP no. 14 —
dan inilah satu-satunya keluaran yang ditujukan **langsung** kepada pimpinan. Bentuk yang
dituju adalah dokumen yang dapat dibaca dan dibacakan lima menit sebelum apel, bukan
dasbor angka kedua.

## Sumber konten: template atas angka, bukan model bahasa

`U-11` mempertanyakan apakah isi Executive Brief disusun **template rule** atau **model
bahasa** (docs/05 §2.12). Endpoint ini menjawab separuh yang tidak memerlukan keputusan
kebijakan: ia mengembalikan **angka beserta dasarnya**, seluruhnya hasil kueri atas data
yang sudah ada. Tidak ada tabel baru, tidak ada kalimat yang disusun mesin, dan tidak ada
model bahasa yang dipanggil — sesuai `docs/13-rencana-integrasi-ai.md` yang masih menunggu
dua keputusan pemilik proyek.

Susunan kalimat pada layar `/brief` berasal dari template tetap yang ditulis di antarmuka,
dan setiap angka di dalam kalimat itu **juga tertera sebagai angka** di halaman yang sama,
sehingga kekeliruan penyusunan kalimat terlihat, bukan tersembunyi (CLAUDE.md §27).

> `TECHNICAL DECISION`, bukan penutupan U-11. Bila kelak diputuskan bahwa narasi boleh
> disusun model bahasa, endpoint ini tetap menjadi sumber angkanya.

## Yang dijaga di sini

1. **Tidak ada ambang yang dihitung ulang.** `risk_class` dan `severity` dibaca dari
   kolomnya masing-masing. Ambang berstatus DEMO / PROPOSED (U-01), sehingga menghitung
   kelas dari skor di lapisan API berarti mengunci angka yang belum disetujui siapa pun
   (CLAUDE.md §11, §12) — aturan yang sama dipakai `routers/map_view.py`.

2. **Setiap angka turunan membawa `*_basis`**, mengikuti `security_index_basis` pada
   `routers/dashboard.py`. Brief dibacakan kepada pimpinan; angka tanpa asal-usul di
   forum itu lebih berbahaya daripada tidak ada angka.

3. **Kewenangan per bagian, bukan hanya per endpoint.** Endpoint memerlukan
   `dashboard:read`, tetapi tiap bagian hanya disertakan bila pengguna benar-benar
   memegang permission atas data yang dirangkumnya (`crime:read`, `warning:read`, …).
   Merangkum data bukan pengecualian dari otorisasi: bila tidak, sebuah role ber-
   `dashboard:read` saja akan membaca ringkasan evaluasi lewat pintu belakang. Cakupan
   wilayah **dan** fungsi diambil dari permission bagian itu sendiri, bukan dari
   `dashboard:read`, sehingga akun Fungsi tidak melihat rekomendasi fungsi lain.

4. **Angkanya harus sama dengan endpoint lain.** Jumlah peringatan aktif di sini adalah
   kueri yang sama dengan `GET /warnings?status=ACTIVE`, dan antrean tindakan adalah pola
   kueri yang sama dengan `GET /operations/pending-decisions`. Brief merangkum sistem yang
   sama, bukan menghitung versinya sendiri.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import (
    CommanderDecision,
    CrimeIncident,
    EarlyWarning,
    Location,
    OperationalAction,
    Prediction,
    PredictionActual,
    Recommendation,
    RiskScore,
)
from ...services import clock
from ..deps import (
    CurrentUser,
    function_filter,
    get_db,
    jurisdiction_filter,
    require_permission,
)
from .evaluation import BASIS as EVALUATION_BASIS
from .operations import DECISIONS_ALLOWING_ACTION

router = APIRouter(prefix="/brief", tags=["executive brief"])

#: Panjang jendela "situasi terakhir". Sama dengan `RECENT_HOURS` pada dashboard supaya
#: kedua layar tidak pernah menyebut jumlah kejadian yang berbeda untuk hari yang sama.
#:
#: Brief **harian**. Spesifikasi §8 menyebut "harian atau per shift", tetapi batas shift
#: adalah aturan organisasi yang belum ditetapkan (CLAUDE.md §2C); mengarang batasnya di
#: sini akan menjadikan angka brief tidak dapat dipertanggungjawabkan.
RECENT_HOURS = 24

#: Banyaknya jenis ancaman yang dibawa brief. Dokumen yang dibacakan lima menit tidak
#: memuat seluruh taksonomi; sisanya tetap dapat dibaca di layar Intelijen.
TOP_THREATS = 3

#: Banyaknya butir antrean tindakan yang dicantumkan. Jumlah totalnya tetap disebut utuh.
PENDING_ACTION_SAMPLE = 5

#: Status rekomendasi yang belum diputus siapa pun (docs/02 §12).
PENDING_REVIEW = "PENDING_REVIEW"

#: Peringatan yang masih menunggu penanganan. Sengaja hanya `ACTIVE` — sama dengan
#: `GET /warnings?status=ACTIVE` dan panel peringatan pada dashboard.
ACTIVE_WARNING = "ACTIVE"


def _wib(moment: datetime) -> str:
    """Waktu dalam WIB untuk teks `*_basis` yang dibaca manusia.

    Penyimpanan tetap UTC; yang berpindah hanya penyajiannya. Dasar perhitungan yang
    menyebut UTC akan membuat pembaca brief mengira jendelanya bergeser tujuh jam.
    """
    return clock.to_jakarta(moment).strftime("%d/%m/%Y %H.%M")


def _no_permission(permission: str) -> str:
    """Bagian yang tidak disertakan tetap menjelaskan dirinya.

    Bagian yang hilang tanpa keterangan tidak dapat dibedakan dari data yang memang
    kosong — dan pada dokumen yang dibacakan kepada pimpinan, perbedaan itu penting.
    """
    return f"Tidak disertakan: akun ini tidak memiliki kewenangan `{permission}`."


def _readable(current: CurrentUser, permission: str) -> tuple[bool, str | None, str | None]:
    """(boleh dibaca, polsek yang boleh dilihat, fungsi yang boleh dilihat).

    Cakupan diambil dari permission bagian itu sendiri. Memakai cakupan `dashboard:read`
    untuk seluruh bagian akan melebarkan kewenangan diam-diam pada role yang cakupannya
    memang berbeda antar-permission (lihat `config/rbac/permissions.yaml`, peran Fungsi).
    """
    if not current.permissions.allows(permission):
        return False, None, None
    return True, jurisdiction_filter(current, permission), function_filter(current, permission)


def _by_polsek(query: Select[Any], polsek: str | None) -> Select[Any]:
    """Menyaring wilayah di query, bukan setelah data terambil."""
    return query if polsek is None else query.where(Location.polsek == polsek)


def _situation(
    session: Session, current: CurrentUser, since: datetime, now: datetime
) -> dict[str, Any]:
    """Bagian 1 — kejadian pada jendela terakhir dan peringatan yang masih menunggu."""
    result: dict[str, Any] = {}

    may_read, polsek, _ = _readable(current, "crime:read")
    if may_read:
        result["incidents_recent"] = (
            session.scalar(
                _by_polsek(
                    select(func.count())
                    .select_from(CrimeIncident)
                    .join(Location, Location.location_id == CrimeIncident.location_id)
                    .where(CrimeIncident.occurred_at.between(since, now)),
                    polsek,
                )
            )
            or 0
        )
        result["incidents_basis"] = (
            f"Kejadian dengan waktu kejadian antara {_wib(since)} dan {_wib(now)} WIB, "
            f"yaitu {RECENT_HOURS} jam terakhir terhadap waktu acuan aplikasi."
        )
    else:
        result["incidents_recent"] = None
        result["incidents_basis"] = _no_permission("crime:read")

    may_read, polsek, _ = _readable(current, "warning:read")
    if may_read:
        warning_query = (
            select(EarlyWarning.severity, func.count())
            .select_from(EarlyWarning)
            .join(Location, Location.location_id == EarlyWarning.location_id)
            .where(EarlyWarning.status == ACTIVE_WARNING)
            .group_by(EarlyWarning.severity)
            .order_by(func.count().desc())
        )
        rows = session.execute(_by_polsek(warning_query, polsek)).all()
        result["active_warnings"] = sum(total for _, total in rows)
        # Tingkat peringatan dibaca dari kolomnya, tidak dihitung ulang dari skor:
        # ambang antar-level belum ditetapkan (U-01).
        result["warnings_by_severity"] = [
            {"severity": severity, "count": total} for severity, total in rows
        ]
        result["warnings_basis"] = (
            "Peringatan dini berstatus ACTIVE — kueri yang sama dengan "
            "`GET /warnings?status=ACTIVE`. Peringatan yang sudah diterima "
            "(ACKNOWLEDGED) atau ditutup (RESOLVED) tidak ikut dihitung. Tingkat "
            "peringatan dibaca apa adanya dari data, bukan dihitung ulang dari skor."
        )
    else:
        result["active_warnings"] = None
        result["warnings_by_severity"] = []
        result["warnings_basis"] = _no_permission("warning:read")

    return result


def _risk_picture(session: Session, current: CurrentUser) -> dict[str, Any]:
    """Bagian 2 dan 3 — wilayah paling berisiko dan ancaman menonjol beserta jam rawannya."""
    may_read, polsek, _ = _readable(current, "risk_score:read")
    if not may_read:
        return {
            "assessment_date": None,
            "top_area": None,
            "top_area_basis": _no_permission("risk_score:read"),
            "top_threats": [],
            "top_threats_basis": _no_permission("risk_score:read"),
        }

    assessment_date = session.scalar(select(func.max(RiskScore.assessment_date)))

    cells_query = (
        select(
            Location.kecamatan,
            RiskScore.threat_type,
            RiskScore.time_window,
            RiskScore.risk_score,
            RiskScore.risk_class,
        )
        .select_from(RiskScore)
        .join(Location, Location.location_id == RiskScore.location_id)
        .where(RiskScore.assessment_date == assessment_date)
        .order_by(RiskScore.risk_score.desc())
    )
    cells = session.execute(_by_polsek(cells_query, polsek)).all()

    top_area = (
        {
            "kecamatan": cells[0].kecamatan,
            "risk_score": int(cells[0].risk_score),
            "risk_class": cells[0].risk_class,
            "threat_type": cells[0].threat_type,
            "time_window": cells[0].time_window,
        }
        if cells
        else None
    )

    # Ancaman menonjol = jenis ancaman dengan sel risiko tertinggi, beserta jendela waktu
    # sel itu sendiri. Jam rawan tidak dirata-ratakan lintas sel: yang berguna bagi
    # pimpinan adalah jam pada sel yang justru menjadi alasan ancaman itu menonjol.
    top_threats: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cell in cells:
        if cell.threat_type in seen:
            continue
        seen.add(cell.threat_type)
        top_threats.append(
            {
                "threat_type": cell.threat_type,
                "kecamatan": cell.kecamatan,
                "time_window": cell.time_window,
                "risk_score": int(cell.risk_score),
                "risk_class": cell.risk_class,
            }
        )
        if len(top_threats) == TOP_THREATS:
            break

    return {
        "assessment_date": assessment_date,
        "top_area": top_area,
        "top_area_basis": (
            "Sel risiko tertinggi pada tanggal penilaian terakhir "
            f"({assessment_date}), beserta kecamatan, jenis ancaman, dan jendela "
            "waktunya. Kelas risiko dibaca dari kolom `risk_scores.risk_class`; "
            "ambangnya berstatus DEMO / PROPOSED (U-01)."
        ),
        "top_threats_basis": (
            f"{TOP_THREATS} jenis ancaman dengan sel risiko tertinggi pada tanggal "
            f"penilaian terakhir ({assessment_date}). Jam rawan adalah jendela waktu "
            "sel tertinggi jenis ancaman itu, bukan rata-rata seluruh selnya."
        ),
        "top_threats": top_threats,
    }


def _awaiting_decision(session: Session, current: CurrentUser) -> dict[str, Any]:
    """Bagian 4 — rekomendasi yang masih menunggu keputusan pimpinan."""
    may_read, polsek, function = _readable(current, "recommendation:read")
    if not may_read:
        return {
            "pending_recommendations": None,
            "pending_by_function": [],
            "pending_recommendations_basis": _no_permission("recommendation:read"),
        }

    query = (
        select(Recommendation.recommended_function, func.count())
        .select_from(Recommendation)
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .where(Recommendation.status == PENDING_REVIEW)
        .group_by(Recommendation.recommended_function)
        .order_by(func.count().desc(), Recommendation.recommended_function)
    )
    if function is not None:
        query = query.where(Recommendation.recommended_function == function)
    rows = session.execute(_by_polsek(query, polsek)).all()

    return {
        "pending_recommendations": sum(total for _, total in rows),
        "pending_by_function": [
            {"recommended_function": name, "count": total} for name, total in rows
        ],
        "pending_recommendations_basis": (
            "Rekomendasi berstatus PENDING_REVIEW — kueri yang sama dengan "
            "`GET /recommendations?status=PENDING_REVIEW`. Rekomendasi adalah usulan, "
            "bukan perintah: selama berstatus ini belum ada pejabat yang memutuskan "
            "(CLAUDE.md §13)."
        ),
    }


def _awaiting_action(session: Session, current: CurrentUser) -> dict[str, Any]:
    """Bagian 5 — keputusan yang sudah diambil tetapi belum ditindaklanjuti.

    Pola kueri sama dengan `GET /operations/pending-decisions`: keputusan `APPROVED`
    atau `MODIFIED` yang belum memiliki baris pada `operational_actions`. Yang berbeda
    hanya bentuk keluarannya — brief menyebut jumlahnya lebih dulu, baru butirannya.
    """
    may_read, polsek, _ = _readable(current, "operation:read")
    if not may_read:
        return {
            "pending_actions": None,
            "pending_action_items": [],
            "pending_actions_basis": _no_permission("operation:read"),
        }

    query = (
        select(CommanderDecision, Recommendation, Location.kecamatan)
        .join(
            Recommendation,
            Recommendation.recommendation_id == CommanderDecision.recommendation_id,
        )
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .outerjoin(
            OperationalAction,
            OperationalAction.decision_id == CommanderDecision.decision_id,
        )
        .where(CommanderDecision.decision.in_(DECISIONS_ALLOWING_ACTION))
        .where(OperationalAction.action_id.is_(None))
        .order_by(CommanderDecision.decision_at.desc())
    )
    query = _by_polsek(query, polsek)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.limit(PENDING_ACTION_SAMPLE)).all()

    return {
        "pending_actions": total,
        "pending_action_items": [
            {
                "decision_code": decision.code,
                "decision": decision.decision,
                "decided_at": decision.decision_at,
                "recommendation_code": recommendation.code,
                "recommended_function": recommendation.recommended_function,
                "priority": recommendation.priority,
                "kecamatan": kecamatan,
                # Usulan asli dan hasil modifikasi dibawa berdampingan, sama seperti
                # layar operasi: yang diperintahkan adalah hasil modifikasi bila ada,
                # dan usulan aslinya tidak pernah ditimpa (U-07).
                "original_recommendation": recommendation.recommendation_text,
                "modified_text": decision.modified_text,
            }
            for decision, recommendation, kecamatan in rows
        ],
        "pending_actions_basis": (
            "Keputusan berstatus "
            f"{' atau '.join(DECISIONS_ALLOWING_ACTION)} yang belum memiliki tindakan "
            "operasional — pola kueri yang sama dengan "
            f"`GET /operations/pending-decisions`. Ditampilkan {PENDING_ACTION_SAMPLE} "
            "butir teratas menurut waktu keputusan; jumlah totalnya disebut utuh."
        ),
    }


def _accuracy(session: Session, current: CurrentUser) -> dict[str, Any]:
    """Bagian 6 — ketepatan model sejauh ini.

    Selalu `PROPOSED`. Aturan pencocokan spasial-temporal antara prediksi dan kejadian
    nyata belum ditetapkan (U-03), sehingga angka precision/recall belum boleh dibacakan
    sebagai capaian final (CLAUDE.md §26). `basis`-nya diambil dari `routers/evaluation.py`
    supaya tidak ada dua penjelasan yang bisa saling menyimpang.
    """
    if not current.permissions.allows("evaluation:read"):
        return {"accuracy": None, "accuracy_basis": _no_permission("evaluation:read")}

    counts: dict[str, int] = {
        match_type: total
        for match_type, total in session.execute(
            select(PredictionActual.match_type, func.count()).group_by(PredictionActual.match_type)
        ).all()
    }
    hits = counts.get("HIT", 0)
    false_positives = counts.get("FALSE_POSITIVE", 0)
    false_negatives = counts.get("FALSE_NEGATIVE", 0)
    predicted = hits + false_positives
    actual = hits + false_negatives

    return {
        "accuracy": {
            "hits": hits,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            # `None` berarti tidak dapat dihitung — berbeda maknanya dari nol.
            "precision": round(hits / predicted, 3) if predicted else None,
            "recall": round(hits / actual, 3) if actual else None,
            "evaluated_rows": sum(counts.values()),
            "status": "PROPOSED",
        },
        "accuracy_basis": EVALUATION_BASIS,
    }


@router.get("/daily", summary="Executive brief harian untuk pimpinan")
def daily(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    """Ringkasan situasi harian, seluruhnya diturunkan dari data yang sudah ada.

    Tidak ada tabel baru dan tidak ada angka yang ditanam di kode. Bagian yang tidak
    boleh dibaca pengguna dikembalikan `null` beserta alasannya, bukan dihilangkan.
    """
    polsek = jurisdiction_filter(current, "dashboard:read")
    since, now = clock.window(RECENT_HOURS)
    local_now = clock.to_jakarta(now)

    brief: dict[str, Any] = {
        "reference_time": now,
        "demo_clock": clock.is_demo_clock(),
        "brief_date": local_now.date(),
        "brief_time": local_now.strftime("%H.%M"),
        "window_hours": RECENT_HOURS,
        "scope_polsek": polsek,
        "scope_basis": (
            f"Seluruh angka dibatasi pada wilayah {polsek}."
            if polsek
            else "Seluruh angka mencakup seluruh wilayah yang boleh dibaca akun ini."
        ),
        "clock_basis": (
            "Waktu acuan aplikasi dipakai sebagai 'sekarang' (keputusan SDL-16): dataset "
            "peragaan berhenti pada Desember 2025, sehingga jendela 24 jam dihitung "
            "terhadap waktu acuan, bukan jam dinding."
            if clock.is_demo_clock()
            else "Waktu sebenarnya dipakai sebagai 'sekarang'."
        ),
    }
    brief.update(_situation(session, current, since, now))
    brief.update(_risk_picture(session, current))
    brief.update(_awaiting_decision(session, current))
    brief.update(_awaiting_action(session, current))
    brief.update(_accuracy(session, current))

    return brief
