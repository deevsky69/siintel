"""TASK 024 — Seed kanal masyarakat: citizen_reports, public_alerts, community_feedback.

Tiga tabel ini sudah bermigrasi sejak TASK 012 tetapi tidak pernah terisi; seedingnya
ditunda pada `docs/09` §5. Modul ini menutup penundaan itu.

**Tidak ada identitas pelapor yang di-seed, dan memang tidak ada tempat untuk menyimpannya.**
`citizen_reports` sengaja tidak memiliki kolom nama, kontak, maupun NIK (docs/02 §6 U-13),
dan keputusan pemilik proyek 1 September 2026 menetapkan masyarakat sebagai **kanal tanpa
akun** (docs/14 §3, §6). Kolom `description` karena itu hanya memuat keterangan kejadian —
bukan keterangan orang.

Yang perlu dibaca bersama data ini (spesifikasi §4):

> laporan masyarakat tidak langsung dianggap sebagai fakta. Laporan harus melalui
> klasifikasi, deteksi duplikasi, deteksi spam, pengelompokan lokasi, penilaian urgensi,
> dan validasi operator/analis sebelum memengaruhi risk score.

Pada prototipe ini **tidak satu pun** tahapan tersebut sudah dibangun, dan laporan
masyarakat **tidak memengaruhi risk score sama sekali** — tidak ada jalur dari
`citizen_reports` ke `risk_scores` maupun `predictions`. `urgency_score` dan
`verification_score` adalah nilai sintetis berstatus `DEMO`, bukan hasil penilaian model
(CLAUDE.md §11, §27). Pernyataan itu ikut dibawa API dan layar, bukan hanya tertulis di sini.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CitizenReport, CommunityFeedback, EarlyWarning, PublicAlert
from . import csv_source as src
from .crime import location_index
from .errors import SeedError
from .master import SeedSummary
from .taxonomy import Taxonomy, load_taxonomy


def _repair_untranslated_status(session: Session, taxonomy: Taxonomy) -> int:
    """Memperbaiki status laporan yang tersimpan sebagai label Bahasa Indonesia.

    DITEMUKAN DI PRODUKSI 9 September 2026. Basis data demo menyimpan `Diterima`,
    `Diteruskan`, dan seterusnya — bukan `RECEIVED`, `FORWARDED`. Barisnya masuk lewat
    versi seeder yang belum memetakan taksonomi, dan karena seed bersifat hanya-menambah,
    tidak ada satu pun jalan yang pernah memperbaikinya.

    Akibatnya tidak kelihatan di layar tetapi menentukan: seluruh kueri menyaring
    `status = 'RECEIVED'`, sehingga produksi melaporkan NOL laporan menunggu verifikasi
    padahal ada 17. Antrean petugas pada aplikasi Android — fitur intinya — kosong.

    YANG SENGAJA TIDAK DILAKUKAN

        Menyegarkan status dari CSV seperti yang dikerjakan untuk `recommendation_text`.
        Kalimat rekomendasi adalah keterangan yang dibangkitkan; status laporan adalah
        KEADAAN OPERASIONAL. Menyegarkannya akan membatalkan verifikasi yang benar-benar
        dilakukan petugas pada demo — kerusakan yang lebih parah daripada yang diperbaiki.

    Karena itu yang disentuh hanya baris yang statusnya BUKAN nilai enum yang sah. Nilai
    seperti itu mustahil lahir dari aplikasi; ia hanya dapat berasal dari seeder lama.
    """
    valid = set(taxonomy.mappings["status_citizen_report"].values())
    stale = session.scalars(select(CitizenReport).where(CitizenReport.status.not_in(valid))).all()

    for report in stale:
        report.status = taxonomy.require("status_citizen_report", report.status)

    return len(stale)


def seed_citizen_reports(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    """Memuat laporan masyarakat.

    `grid_id` boleh kosong: `citizen_reports.location_id` nullable justru karena laporan
    masuk dengan koordinat bebas dan baru dipetakan ke grid setelah geo-processing
    (docs/02 §6). Baris tanpa grid **tidak** dipaksa masuk ke sel terdekat — memilihkan
    lokasi untuk pelapor berarti mengarang data.
    """
    existing = set(session.scalars(select(CitizenReport.code)).all())
    locations = location_index(session)
    inserted = 0
    unmapped = 0
    repaired = _repair_untranslated_status(session, taxonomy)

    for row in src.read_rows("citizen_reports.csv"):
        code = src.required_text(row, "report_id", "citizen_reports.csv")
        if code in existing:
            continue

        where = f"citizen_reports.csv:{code}"
        grid_id = src.text(row, "grid_id")
        location_id = None
        if grid_id is not None:
            location_id = locations.get(grid_id)
            if location_id is None:
                message = f"{where}: grid_id '{grid_id}' tidak ada pada tabel locations"
                raise SeedError(message)
        else:
            unmapped += 1

        latitude = float(src.required_text(row, "latitude", where))
        longitude = float(src.required_text(row, "longitude", where))
        incident_time = src.text(row, "incident_time")

        session.add(
            CitizenReport(
                code=code,
                reported_at=src.parse_datetime(src.required_text(row, "reported_at", where), where),
                incident_time=(
                    None if incident_time is None else src.parse_datetime(incident_time, where)
                ),
                category=src.required_text(row, "category", where),
                description=src.text(row, "description"),
                latitude=latitude,
                longitude=longitude,
                geom=f"SRID=4326;POINT({longitude} {latitude})",
                location_id=location_id,
                location_text=src.text(row, "location_text"),
                urgency_score=src.integer(row, "urgency_score"),
                verification_score=src.integer(row, "verification_score"),
                status=taxonomy.require("status_citizen_report", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("citizen_reports", inserted, len(existing))
    catatan = []
    if unmapped:
        catatan.append(f"{unmapped} laporan belum tertaut ke sel grid")
    if repaired:
        catatan.append(f"{repaired} status berbahasa Indonesia diperbaiki")
    if catatan:
        summary.note("citizen_reports", "; ".join(catatan))


def seed_public_alerts(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    """Memuat imbauan publik.

    Tabelnya sengaja tanpa `location_id`: imbauan memakai `area_text` supaya grid internal
    tidak ikut terbawa ke luar (docs/02 §7, CLAUDE.md §24).
    """
    existing = set(session.scalars(select(PublicAlert.code)).all())
    warnings = {
        code: warning_id
        for code, warning_id in session.execute(
            select(EarlyWarning.code, EarlyWarning.warning_id)
        ).all()
    }
    inserted = 0

    for row in src.read_rows("public_alerts.csv"):
        code = src.required_text(row, "public_alert_id", "public_alerts.csv")
        if code in existing:
            continue

        where = f"public_alerts.csv:{code}"
        warning_code = src.text(row, "warning_id")
        warning_id = None
        if warning_code is not None:
            warning_id = warnings.get(warning_code)
            if warning_id is None:
                message = (
                    f"{where}: peringatan '{warning_code}' tidak ada pada tabel early_warnings"
                )
                raise SeedError(message)

        session.add(
            PublicAlert(
                code=code,
                warning_id=warning_id,
                severity=taxonomy.require("severity", src.text(row, "severity")),
                threat_type=src.required_text(row, "threat_type", where),
                area_text=src.required_text(row, "area_text", where),
                time_window=src.text(row, "time_window"),
                window_start=src.parse_datetime(
                    src.required_text(row, "window_start", where), where
                ),
                window_end=src.parse_datetime(src.required_text(row, "window_end", where), where),
                status=taxonomy.require("status_public_alert", src.text(row, "status")),
                public_message=src.required_text(row, "public_message", where),
            )
        )
        inserted += 1

    summary.record("public_alerts", inserted, len(existing))


def seed_community_feedback(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(CommunityFeedback.code)).all())
    reports = {
        code: report_id
        for code, report_id in session.execute(
            select(CitizenReport.code, CitizenReport.report_id)
        ).all()
    }
    inserted = 0

    for row in src.read_rows("community_feedback.csv"):
        code = src.required_text(row, "feedback_id", "community_feedback.csv")
        if code in existing:
            continue

        where = f"community_feedback.csv:{code}"
        report_code = src.required_text(row, "report_id", where)
        report_id = reports.get(report_code)
        if report_id is None:
            message = f"{where}: laporan '{report_code}' tidak ada pada tabel citizen_reports"
            raise SeedError(message)

        session.add(
            CommunityFeedback(
                code=code,
                report_id=report_id,
                feedback_type=taxonomy.require("feedback_type", src.text(row, "feedback_type")),
                submitted_at=src.parse_datetime(
                    src.required_text(row, "submitted_at", where), where
                ),
                status=taxonomy.require("status_community_feedback", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("community_feedback", inserted, len(existing))


def seed_public_data(session: Session, taxonomy: Taxonomy | None = None) -> SeedSummary:
    """Menjalankan seluruh seed kanal masyarakat TASK 024."""
    resolved = taxonomy or load_taxonomy()
    summary = SeedSummary()

    seed_citizen_reports(session, resolved, summary)
    session.flush()
    seed_public_alerts(session, resolved, summary)
    session.flush()
    seed_community_feedback(session, resolved, summary)

    # Session dibuat dengan `autoflush=False`, sehingga baris terakhir kelompok ini
    # tidak akan terlihat oleh query kelompok berikutnya bila tidak di-flush di sini.
    # Itulah yang membuat `seeding all` gagal di database kosong sementara menjalankan
    # perintah satu per satu berhasil: setiap perintah punya transaksinya sendiri.
    session.flush()

    return summary


__all__ = [
    "seed_citizen_reports",
    "seed_community_feedback",
    "seed_public_alerts",
    "seed_public_data",
]
