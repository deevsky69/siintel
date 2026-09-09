"""Layar Pimpinan — ringkasan keadaan untuk pengambil keputusan (TASK 150).

Permintaan pemilik proyek, 2 September 2026. Berbeda dari `/dashboard/summary` yang
menyajikan indeks dan agregat teknis, layar ini disusun mengikuti urutan pertanyaan yang
benar-benar diajukan seorang pimpinan saat membuka layar:

```text
apa yang masuk hari ini
        v
bagaimana keadaan wilayah saya
        v
apa yang menuntut perhatian saya sekarang
        v
di mana saya harus menaruh sumber daya
```

EMPAT HAL YANG MENENTUKAN BENTUK MODUL INI

1. **Tidak ada ambang di kode ini.** Nama status wilayah (Aman/Waspada/Siaga) dan tingkat
   volume laporan (Kritis/Sedang/Rendah) dibaca dari `config/risk/warning-thresholds.yaml`
   blok `leadership_display`, beserta statusnya. Menyalinnya ke sini akan menaruh ambang
   kedua di luar satu-satunya tempat yang boleh memuatnya (CLAUDE.md §12).

2. **Empat kelas risiko dipetakan ke tiga nama status, dan penggabungan itu dinyatakan.**
   Respons selalu membawa `area_status_mapping` beserta `status: PROPOSED`; layar
   menampilkannya. Pemetaan yang tidak terlihat akan terbaca sebagai kelas resmi.

3. **"Laporan" bukan satu hal.** Sistem memuat tiga jenis catatan yang sama-sama disebut
   laporan — kejadian kriminal, laporan intelijen, laporan masyarakat. Ketiganya dicacah
   terpisah dan dijumlahkan; menampilkan satu angka gabungan tanpa rinciannya akan membuat
   pembaca menyimpulkan hal yang berbeda dari yang sebenarnya dihitung.

4. **Rekomendasi kebijakan diturunkan dari agregat yang benar-benar dihitung**, bukan
   dikarang, dan setiap butirnya membawa `basis` yang menyebut angka asalnya. Seluruhnya
   berlabel `RULE`: belum ada model yang menghasilkannya, dan menyebutnya keluaran AI akan
   menjadi penjelasan fiktif (CLAUDE.md §27).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import (
    CitizenReport,
    CrimeIncident,
    EarlyWarning,
    IntelligenceReport,
    Location,
    Prediction,
    Recommendation,
    RiskScore,
)
from ...services import clock
from ...services.risk_engine import load_leadership_display
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

#: Jendela "hari ini" pada kartu pertama.
RECENT_HOURS = 24

#: Panjang jendela "isu menonjol", beserta jendela pembanding sebelumnya yang sama panjang.
ISSUE_DAYS = 7

#: Banyaknya baris pada daftar "Top area rawan". Permintaan pemilik proyek: 10.
TOP_AREA_LIMIT = 10

#: Jendela daftar "Top area rawan", dalam hari.
#:
#: Tiga puluh hari, bukan tujuh seperti daftar isu menonjol. Pada tujuh hari, wilayah
#: teratas hanya mengumpulkan enam laporan dan wilayah terbawah satu — selisih sebesar itu
#: berayun karena satu-dua laporan saja, sehingga peringkat Kritis/Sedang/Rendah lebih
#: banyak memantulkan kebetulan daripada pola.
TOP_AREA_DAYS = 30

#: Banyaknya wilayah prioritas pada kartu keempat.
PRIORITY_AREA_LIMIT = 3

#: Jatah baris per jenis pada daftar "perlu perhatian segera".
#:
#: Dibagi per jenis, **bukan** diambil delapan teratas menurut skor. Pengambilan menurut
#: skor terlihat lebih obyektif, tetapi pada data ini seluruh delapan baris terisi
#: peringatan CRITICAL dan rekomendasi yang menunggu keputusan tidak pernah muncul —
#: padahal rekomendasi adalah satu-satunya butir yang hanya dapat diselesaikan oleh
#: pimpinan sendiri. Daftar yang menyembunyikannya membuat layar ini gagal pada tugas
#: utamanya.
ATTENTION_QUOTA = {"EARLY_WARNING": 4, "RECOMMENDATION": 3, "CITIZEN_REPORT": 1}

#: Status yang menandai sesuatu masih menunggu manusia.
WARNING_ACTIVE = "ACTIVE"
RECOMMENDATION_PENDING = "PENDING_REVIEW"
CITIZEN_REPORT_UNVERIFIED = "RECEIVED"

REPORTS_BASIS = (
    "Tiga jenis catatan dicacah terpisah karena ketiganya berbeda asal dan berbeda "
    "keandalan: crime_incidents (kejadian yang sudah terverifikasi), intelligence_reports "
    "(laporan intelijen), dan citizen_reports (laporan masyarakat, termasuk yang belum "
    "diverifikasi). Kejadian dan laporan masyarakat dicacah pada 24 jam terakhir terhadap "
    "waktu acuan aplikasi. Laporan intelijen hanya menyimpan report_date tanpa jam, "
    "sehingga yang dicacah adalah HARI acuan penuh — bukan 24 jam bergulir. "
    "Sebagian laporan masyarakat tidak memiliki lokasi yang cocok dengan master lokasi; "
    "bagi pengguna tanpa batas wilayah laporan itu tetap dicacah dan jumlahnya disebut "
    "terpisah, sedangkan bagi pengguna ber-cakupan wilayah ia tidak ditampilkan karena "
    "tidak dapat dipastikan berada di wilayahnya."
)

ATTENTION_BASIS = (
    "Yang masuk daftar ini hanya hal yang masih menunggu manusia: peringatan berstatus "
    "ACTIVE (belum diterima siapa pun), rekomendasi berstatus PENDING_REVIEW (belum "
    "diputus komandan), dan laporan masyarakat berstatus RECEIVED (belum diverifikasi). "
    "Hal yang sudah diterima, diputus, atau diverifikasi TIDAK ikut walaupun skornya "
    "tinggi — daftar ini menuntut tindakan, bukan melaporkan keadaan."
)

POLICY_BASIS = (
    "Rekomendasi di bawah diturunkan dengan ATURAN dari agregat yang benar-benar dihitung "
    "pada layar ini, bukan dihasilkan model. Setiap butir menyebut angka asalnya. Tidak ada "
    "satu pun yang berasal dari kalender kegiatan (car free day, hari besar, agenda "
    "unjuk rasa terdaftar) karena sistem belum memuat data itu — menambahkannya menuntut "
    "sumber data baru, bukan sekadar aturan baru."
)


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


def _citizen_scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    """Seperti `_scoped`, tetapi menangani laporan masyarakat **tanpa lokasi**.

    Sebagian `citizen_reports` tidak memiliki `location_id` — pelapor tidak selalu dapat
    menyebut lokasi yang cocok dengan master lokasi. `JOIN` biasa membuang baris itu
    diam-diam, sehingga kartu di layar menyebut angka yang lebih kecil daripada kenyataan
    tanpa apa pun yang menjelaskan selisihnya.

    Perlakuannya sengaja dibedakan menurut kewenangan:

    - **pengguna ber-cakupan wilayah** tidak melihatnya, karena laporan tanpa lokasi tidak
      dapat dipastikan berada di wilayahnya — menampilkannya berarti menebak;
    - **pengguna tanpa batas wilayah** melihat seluruhnya, karena bagi mereka tidak ada
      yang perlu ditebak.
    """
    if polsek is None:
        return query.outerjoin(Location, Location.location_id == CitizenReport.location_id)
    return query.join(Location, Location.location_id == CitizenReport.location_id).where(
        Location.polsek == polsek
    )


def _reference() -> tuple[datetime, date]:
    now = clock.reference_now()
    return now, now.astimezone(clock.JAKARTA).date()


# ---------------------------------------------------------------------------
# 1. Laporan 24 jam terakhir
# ---------------------------------------------------------------------------


def _reports_24h(session: Session, polsek: str | None) -> dict[str, Any]:
    now, today = _reference()
    since = now - timedelta(hours=RECENT_HOURS)

    incidents = session.scalar(
        _scoped(
            select(func.count())
            .select_from(CrimeIncident)
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(CrimeIncident.occurred_at >= since, CrimeIncident.occurred_at <= now),
            polsek,
        )
    )
    citizen = session.scalar(
        _citizen_scoped(
            select(func.count()).select_from(CitizenReport),
            polsek,
        ).where(CitizenReport.reported_at >= since, CitizenReport.reported_at <= now)
    )
    # Laporan intelijen hanya bertanggal, tanpa jam — dicacah per hari acuan penuh dan
    # dinyatakan demikian, bukan dipaksa masuk jendela 24 jam yang tidak dapat dijawabnya.
    intelligence = session.scalar(
        _scoped(
            select(func.count())
            .select_from(IntelligenceReport)
            .join(Location, Location.location_id == IntelligenceReport.location_id)
            .where(IntelligenceReport.report_date == today),
            polsek,
        )
    )

    counts = {
        "crime_incidents": int(incidents or 0),
        "citizen_reports": int(citizen or 0),
        "intelligence_reports": int(intelligence or 0),
    }
    citizen_without_location = session.scalar(
        _citizen_scoped(select(func.count()).select_from(CitizenReport), polsek).where(
            CitizenReport.reported_at >= since,
            CitizenReport.reported_at <= now,
            CitizenReport.location_id.is_(None),
        )
    )
    return {
        **counts,
        "total": sum(counts.values()),
        "citizen_reports_without_location": int(citizen_without_location or 0),
        "window_start": since,
        "window_end": now,
        "intelligence_date": today,
        "basis": REPORTS_BASIS,
    }


# ---------------------------------------------------------------------------
# 2. Status wilayah
# ---------------------------------------------------------------------------


def _latest_assessment_date(session: Session, polsek: str | None) -> Any:
    return session.scalar(
        _scoped(
            select(func.max(RiskScore.assessment_date))
            .select_from(RiskScore)
            .join(Location, Location.location_id == RiskScore.location_id),
            polsek,
        )
    )


AREA_STATUS_SCOPE = (
    "Status satu kecamatan mengikuti SEL DENGAN SKOR TERTINGGI di dalamnya, sama seperti "
    "layer risiko berjalan pada peta. Definisi itu sengaja disamakan: dua layar yang "
    "menjawab 'berapa risiko di Tebet' dengan angka yang berbeda akan saling meruntuhkan "
    "kepercayaan, dan tidak ada di layar yang akan menunjukkan mana yang benar. "
    "Rata-rata seluruh sel ikut dikembalikan supaya selisih antara 'sel terburuk' dan "
    "'keadaan menyeluruh' terbaca — keduanya menjawab pertanyaan yang berbeda."
)


def _area_status(session: Session, polsek: str | None) -> dict[str, Any]:
    display = load_leadership_display()
    assessment_date = _latest_assessment_date(session, polsek)

    areas: list[dict[str, Any]] = []
    if assessment_date is not None:
        rows = session.execute(
            _scoped(
                select(
                    Location.kecamatan,
                    RiskScore.risk_score,
                    RiskScore.risk_class,
                )
                .select_from(RiskScore)
                .join(Location, Location.location_id == RiskScore.location_id)
                .where(RiskScore.assessment_date == assessment_date),
                polsek,
            )
        ).all()

        grouped: dict[str, list[tuple[int, str | None]]] = {}
        for kecamatan, score, risk_class in rows:
            grouped.setdefault(str(kecamatan), []).append((int(score), risk_class))

        for kecamatan, cells in grouped.items():
            # Kelas diambil dari baris yang benar-benar menghasilkan puncak, bukan dihitung
            # ulang dari skornya: menerapkan ambang untuk kedua kalinya di sini akan
            # menaruh salinan ambang di luar config/risk/ (CLAUDE.md §12).
            peak_score, peak_class = max(cells, key=lambda cell: cell[0])
            areas.append(
                {
                    "kecamatan": kecamatan,
                    "risk_score": peak_score,
                    "risk_class": peak_class,
                    "average_risk_score": round(sum(cell[0] for cell in cells) / len(cells)),
                    "cell_count": len(cells),
                    **display.status_for(peak_class),
                }
            )

    areas.sort(key=lambda row: int(row["risk_score"]), reverse=True)
    tally: dict[str, int] = {}
    for area in areas:
        key = str(area["status"])
        tally[key] = tally.get(key, 0) + 1

    return {
        "assessment_date": assessment_date,
        "areas": areas,
        "tally": [
            {"status": row["status"], "label": row["label"], "areas": tally.get(row["status"], 0)}
            for row in display.area_status
        ],
        "mapping": [dict(row) for row in display.area_status],
        "mapping_status": display.area_status_status,
        "basis": f"{AREA_STATUS_SCOPE} {display.area_status_basis}",
    }


# ---------------------------------------------------------------------------
# 3. Perlu perhatian segera
# ---------------------------------------------------------------------------


def _needs_attention(session: Session, polsek: str | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    warnings = session.execute(
        _scoped(
            select(EarlyWarning, Location.kecamatan)
            .join(Location, Location.location_id == EarlyWarning.location_id)
            .where(EarlyWarning.status == WARNING_ACTIVE)
            .order_by(EarlyWarning.risk_score.desc(), EarlyWarning.window_start),
            polsek,
        ).limit(ATTENTION_QUOTA["EARLY_WARNING"])
    ).all()
    items.extend(
        {
            "kind": "EARLY_WARNING",
            "code": warning.code,
            "headline": f"Peringatan {warning.severity} — {warning.threat_type}",
            "kecamatan": kecamatan,
            "detail": (
                f"Skor {warning.risk_score}, jendela {warning.time_window or 'tidak disebut'}"
            ),
            "why": "Belum diterima siapa pun.",
            "since": warning.window_start,
            "rank": int(warning.risk_score),
            "href": f"/peringatan?kode={warning.code}",
        }
        for warning, kecamatan in warnings
    )

    pending = session.execute(
        _scoped(
            select(Recommendation, Location.kecamatan)
            .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
            .join(Location, Location.location_id == Prediction.location_id)
            .where(Recommendation.status == RECOMMENDATION_PENDING)
            .order_by(Prediction.risk_score.desc()),
            polsek,
        ).limit(ATTENTION_QUOTA["RECOMMENDATION"])
    ).all()
    items.extend(
        {
            "kind": "RECOMMENDATION",
            "code": recommendation.code,
            "headline": f"Rekomendasi menunggu keputusan — {recommendation.recommended_function}",
            "kecamatan": kecamatan,
            "detail": recommendation.recommendation_text,
            "why": "Belum disetujui, dimodifikasi, maupun ditolak.",
            "since": recommendation.created_at,
            "rank": 0,
            "href": f"/rekomendasi?kode={recommendation.code}",
        }
        for recommendation, kecamatan in pending
    )

    unverified = session.scalar(
        _citizen_scoped(select(func.count()).select_from(CitizenReport), polsek).where(
            CitizenReport.status == CITIZEN_REPORT_UNVERIFIED
        )
    )
    if unverified:
        items.append(
            {
                "kind": "CITIZEN_REPORT",
                "code": None,
                "headline": f"{int(unverified)} laporan masyarakat belum diverifikasi",
                "kecamatan": None,
                "detail": "Laporan berstatus RECEIVED menunggu verifikasi petugas.",
                "why": "Belum diverifikasi, sehingga belum dapat menjadi dasar tindakan.",
                "since": None,
                "rank": int(unverified),
                "href": "/masyarakat?status=RECEIVED",
            }
        )

    # Peringatan aktif didahulukan: ia satu-satunya butir yang membawa jendela waktu yang
    # dapat lewat. Rekomendasi dan laporan tidak kedaluwarsa dengan cara yang sama.
    order = {"EARLY_WARNING": 0, "RECOMMENDATION": 1, "CITIZEN_REPORT": 2}
    items.sort(key=lambda row: (order[str(row["kind"])], -int(row["rank"])))
    return items


# ---------------------------------------------------------------------------
# 4 & 5. Wilayah prioritas dan Top area menurut jumlah laporan
# ---------------------------------------------------------------------------


def _report_counts_by_area(
    session: Session, polsek: str | None, since: date, until: date
) -> list[tuple[str, int, int, int]]:
    """Cacah ketiga jenis laporan per kecamatan pada satu rentang tanggal."""

    def counts(model: Any, column: Any) -> dict[str, int]:
        rows = session.execute(
            _scoped(
                select(Location.kecamatan, func.count())
                .select_from(model)
                .join(Location, Location.location_id == model.location_id)
                .where(column >= since, column <= until)
                .group_by(Location.kecamatan),
                polsek,
            )
        ).all()
        return {str(name): int(total) for name, total in rows}

    incidents = counts(CrimeIncident, CrimeIncident.incident_date)
    intelligence = counts(IntelligenceReport, IntelligenceReport.report_date)
    # Laporan masyarakat tanpa lokasi tidak dapat dibebankan ke kecamatan mana pun; ia
    # dicacah terpisah pada `unattributed_reports`, bukan dibuang tanpa jejak.
    citizen = counts(CitizenReport, func.date(CitizenReport.reported_at))

    names = set(incidents) | set(intelligence) | set(citizen)
    return [
        (name, incidents.get(name, 0), intelligence.get(name, 0), citizen.get(name, 0))
        for name in names
    ]


def _top_report_areas(session: Session, polsek: str | None, days: int) -> dict[str, Any]:
    display = load_leadership_display()
    _, today = _reference()
    since = today - timedelta(days=days - 1)

    rows = _report_counts_by_area(session, polsek, since, today)
    tallied: list[dict[str, Any]] = [
        {
            "kecamatan": name,
            "crime_incidents": incidents,
            "intelligence_reports": intelligence,
            "citizen_reports": citizen,
            "reports": incidents + intelligence + citizen,
        }
        for name, incidents, intelligence, citizen in rows
    ]
    totals = sorted(tallied, key=lambda row: int(row["reports"]), reverse=True)

    unattributed = session.scalar(
        _citizen_scoped(select(func.count()).select_from(CitizenReport), polsek).where(
            func.date(CitizenReport.reported_at) >= since,
            func.date(CitizenReport.reported_at) <= today,
            CitizenReport.location_id.is_(None),
        )
    )

    peak = max((int(row["reports"]) for row in totals), default=0)
    ranked = [
        {**row, **display.volume_for(int(row["reports"]), peak)} for row in totals[:TOP_AREA_LIMIT]
    ]

    return {
        "days": days,
        "window_from": since,
        "window_to": today,
        "peak_reports": peak,
        # Laporan tanpa lokasi tidak muncul di baris mana pun karena memang tidak dapat
        # dibebankan ke satu kecamatan. Jumlahnya disebut supaya daftar ini tidak terbaca
        # sebagai seluruh laporan pada jendela tersebut.
        "unattributed_reports": int(unattributed or 0),
        "areas": ranked,
        "level_status": display.report_volume_status,
        "basis": display.report_volume_basis,
    }


def _priority_areas(area_status: dict[str, Any]) -> list[dict[str, Any]]:
    """Wilayah berisiko tertinggi, diambil dari status wilayah yang sudah dihitung.

    Sengaja tidak menghitung ulang: dua daftar yang menjawab pertanyaan yang sama tetapi
    dihitung dua kali dapat berselisih, dan tidak ada di layar yang akan menunjukkannya.
    """
    areas: list[dict[str, Any]] = area_status["areas"]
    return areas[:PRIORITY_AREA_LIMIT]


# ---------------------------------------------------------------------------
# 6. Isu menonjol sepekan
# ---------------------------------------------------------------------------


def _prominent_issues(session: Session, polsek: str | None) -> dict[str, Any]:
    _, today = _reference()
    since = today - timedelta(days=ISSUE_DAYS - 1)
    previous_until = since - timedelta(days=1)
    previous_since = previous_until - timedelta(days=ISSUE_DAYS - 1)

    def by_type(start: date, end: date) -> dict[str, int]:
        rows = session.execute(
            _scoped(
                select(CrimeIncident.incident_type, func.count())
                .select_from(CrimeIncident)
                .join(Location, Location.location_id == CrimeIncident.location_id)
                .where(CrimeIncident.incident_date >= start, CrimeIncident.incident_date <= end)
                .group_by(CrimeIncident.incident_type),
                polsek,
            )
        ).all()
        return {str(name): int(total) for name, total in rows}

    current = by_type(since, today)
    previous = by_type(previous_since, previous_until)

    tallied: list[dict[str, Any]] = [
        {
            "threat_type": name,
            "incidents": total,
            "previous_incidents": previous.get(name, 0),
            # Selisih mentah, bukan persentase: dari basis 1 kejadian menjadi 3,
            # "naik 200%" terbaca jauh lebih dramatis daripada kenyataannya.
            "change": total - previous.get(name, 0),
        }
        for name, total in current.items()
    ]
    issues = sorted(tallied, key=lambda row: int(row["incidents"]), reverse=True)

    return {
        "days": ISSUE_DAYS,
        "window_from": since,
        "window_to": today,
        "previous_from": previous_since,
        "previous_to": previous_until,
        "issues": issues,
        "basis": (
            "Cacah kejadian per jenis gangguan pada 7 hari terakhir, dibandingkan terhadap "
            "7 hari sebelumnya. Perubahan disajikan sebagai SELISIH kejadian, bukan persen: "
            "dari basis yang kecil, persentase melebih-lebihkan perubahan yang sebenarnya "
            "hanya beberapa kejadian."
        ),
    }


# ---------------------------------------------------------------------------
# 7. Rekomendasi kebijakan
# ---------------------------------------------------------------------------


def _peak_hour_band(session: Session, polsek: str | None, kecamatan: str, days: int) -> Any:
    """Jam tersibuk kejadian di satu kecamatan, sebagai rentang tiga jam."""
    _, today = _reference()
    since = today - timedelta(days=days - 1)

    rows = session.execute(
        _scoped(
            select(func.extract("hour", CrimeIncident.incident_time), func.count())
            .select_from(CrimeIncident)
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(
                Location.kecamatan == kecamatan,
                CrimeIncident.incident_date >= since,
                CrimeIncident.incident_date <= today,
            )
            .group_by(func.extract("hour", CrimeIncident.incident_time)),
            polsek,
        )
    ).all()
    if not rows:
        return None

    counts = {int(hour): int(total) for hour, total in rows}
    # Jendela tiga jam bergulir: satu jam tunggal terlalu sempit untuk menjadi dasar
    # penjadwalan patroli, dan puncak satu jam mudah berpindah karena kebetulan.
    best_start, best_total = max(
        (
            (start, sum(counts.get((start + offset) % 24, 0) for offset in range(3)))
            for start in range(24)
        ),
        key=lambda pair: pair[1],
    )
    if best_total == 0:
        return None
    return {
        "start_hour": best_start,
        "end_hour": (best_start + 3) % 24,
        "incidents": best_total,
        "days": days,
    }


#: Panjang jendela yang dipakai mencari jam rawan. Lebih panjang daripada jendela isu
#: sepekan dengan sengaja: pola jam menuntut lebih banyak kejadian untuk terlihat.
PEAK_HOUR_DAYS = 90


def _policy_recommendations(
    session: Session,
    polsek: str | None,
    priority_areas: list[dict[str, Any]],
    issues: dict[str, Any],
    attention: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rekomendasi kebijakan yang diturunkan aturan, masing-masing dengan tujuannya.

    Setiap butir membawa `href` ke layar yang memuat ANGKA ASALNYA — bukan ke layar yang
    sekadar berkaitan. Butir jam patroli menunjuk rincian kecamatan yang skornya dikutip,
    butir operasi khusus menunjuk analitik yang sudah tersaring ke jenis gangguan itu, dan
    butir verifikasi menunjuk daftar laporan berstatus RECEIVED yang jumlahnya disebut.
    Tanpa itu, pembaca yang ingin memeriksa dasar sebuah saran harus menebak sendiri ke
    mana harus pergi — dan saran yang dasarnya tak dapat diperiksa adalah persis yang
    dilarang CLAUDE.md §27.

    Alamat web muncul di respons API mengikuti kebiasaan yang sudah ada pada daftar
    `needs_attention` di berkas yang sama; keduanya melayani konsumen yang sama.
    """
    items: list[dict[str, Any]] = []

    top_area = priority_areas[0] if priority_areas else None
    if top_area is not None:
        band = _peak_hour_band(session, polsek, str(top_area["kecamatan"]), PEAK_HOUR_DAYS)
        if band is not None:
            items.append(
                {
                    "action": (
                        f"Tambah patroli pukul {band['start_hour']:02d}.00 s.d. "
                        f"{band['end_hour']:02d}.00 WIB di {top_area['kecamatan']}"
                    ),
                    "function": "Samapta",
                    "basis": (
                        f"{top_area['kecamatan']} berstatus {top_area['label']} dengan skor "
                        f"{top_area['risk_score']}, dan {band['incidents']} kejadian dalam "
                        f"{band['days']} hari terakhir di sana jatuh pada rentang jam itu — "
                        "rentang tersibuk dari 24 rentang tiga jam yang diperiksa."
                    ),
                    "source": "RULE",
                    "href": f"/wilayah/{quote(str(top_area['kecamatan']))}",
                }
            )

    rising = [row for row in issues["issues"] if int(row["change"]) > 0]
    if rising:
        top_issue = max(rising, key=lambda row: int(row["change"]))
        items.append(
            {
                "action": f"Operasi khusus terarah pada {top_issue['threat_type']}",
                "function": "Reskrim",
                "basis": (
                    f"{top_issue['threat_type']} naik dari {top_issue['previous_incidents']} "
                    f"menjadi {top_issue['incidents']} kejadian dibanding pekan sebelumnya — "
                    f"kenaikan terbesar di antara seluruh jenis gangguan pekan ini."
                ),
                "source": "RULE",
                "href": f"/analitik?jenis={quote(str(top_issue['threat_type']))}",
            }
        )

    unverified = next(
        (row for row in attention if str(row["kind"]) == "CITIZEN_REPORT"),
        None,
    )
    if unverified is not None:
        items.append(
            {
                "action": "Percepat verifikasi laporan masyarakat yang tertahan",
                "function": "Binmas",
                "basis": (
                    f"{unverified['rank']} laporan masih berstatus RECEIVED. Selama belum "
                    "diverifikasi, laporan itu tidak dapat menjadi dasar tindakan maupun "
                    "masuk ke penilaian risiko."
                ),
                "source": "RULE",
                "href": "/masyarakat?status=RECEIVED",
            }
        )

    return {
        "recommendations": items,
        "basis": POLICY_BASIS,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/leadership", summary="Ringkasan keadaan untuk layar Pimpinan")
def leadership(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "dashboard:read")
    now, _ = _reference()

    area_status = _area_status(session, polsek)
    attention = _needs_attention(session, polsek)
    issues = _prominent_issues(session, polsek)
    priority = _priority_areas(area_status)

    return {
        "reference_time": now,
        "demo_clock": clock.is_demo_clock(),
        "reports_24h": _reports_24h(session, polsek),
        "area_status": area_status,
        "needs_attention": {"items": attention, "basis": ATTENTION_BASIS},
        "priority_areas": priority,
        "top_report_areas": _top_report_areas(session, polsek, days=TOP_AREA_DAYS),
        "prominent_issues": issues,
        "policy": _policy_recommendations(session, polsek, priority, issues, attention),
    }
