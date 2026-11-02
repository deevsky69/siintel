"""Buletin mingguan kelurahan — menyusun teks dari data minggu sebelumnya.

Isi (satu kelurahan, satu minggu Senin–Minggu):
1. Kejadian 3C yang tercatat di kelurahan itu, per jenis (crime_incidents, mengikuti batas
   tampilan data).
2. Imbauan yang sedang berlaku untuk kecamatannya (public_alerts ACTIVE).
3. Rekomendasi yang SUDAH DISETUJUI/DIUBAH Pimpinan untuk prediksi di kelurahan itu pada
   minggu tersebut — bukan usulan mentah sistem.
4. Saran umum per jenis dari config/recommendation/function-rules.yaml.

Teksnya aturan, bukan model bahasa; angkanya tersimpan di `figures` supaya dapat diperiksa.
Ia DRAFT sampai disetujui pemegang `bulletin:approve`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, Prediction, PublicAlert, Recommendation
from . import clock
from . import patrol_plan as planning
from .warning_issuance import load_function_rules

DECIDED_STATUSES = ("APPROVED", "MODIFIED")
THREAT_LABEL = {
    "CURANMOR": "pencurian kendaraan bermotor",
    "CURAT": "pencurian dengan pemberatan",
    "CURAS": "pencurian dengan kekerasan",
}
BASIS = (
    "Buletin disusun sistem dari kejadian tercatat minggu itu di kelurahan tersebut, imbauan "
    "yang berlaku, dan rekomendasi yang sudah disetujui Pimpinan; disetujui pemegang "
    "bulletin:approve sebelum dikirim. Bukan model bahasa; angkanya di `figures`."
)


def last_full_week(reference: date | None = None) -> date:
    """Senin dari minggu penuh terakhir sebelum tanggal acuan."""
    today = reference or clock.reference_now().astimezone(clock.JAKARTA).date()
    this_monday = today - timedelta(days=today.weekday())
    return this_monday - timedelta(days=7)


def compose(
    session: Session, kelurahan: str, kecamatan: str, polsek: str, week_start: date
) -> tuple[str, dict[str, Any]]:
    week_end = week_start + timedelta(days=6)
    threats = planning._threats()
    counts = {
        str(threat): int(count)
        for threat, count in session.execute(
            select(CrimeIncident.incident_type, func.count())
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(
                Location.kelurahan == kelurahan,
                CrimeIncident.incident_date >= week_start,
                CrimeIncident.incident_date <= week_end,
                CrimeIncident.incident_type.in_(threats),
            )
            .group_by(CrimeIncident.incident_type)
        ).all()
    }
    alerts = session.scalars(
        select(PublicAlert)
        .where(PublicAlert.status == "ACTIVE", PublicAlert.area_text.ilike(f"%{kecamatan}%"))
        .order_by(PublicAlert.created_at.desc())
        .limit(3)
    ).all()
    decided = session.execute(
        select(
            Recommendation.recommendation_text,
            Recommendation.recommended_function,
            Recommendation.status,
        )
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .where(
            Location.kelurahan == kelurahan,
            Recommendation.status.in_(DECIDED_STATUSES),
            func.date(Prediction.window_start) >= week_start,
            func.date(Prediction.window_start) <= week_end + timedelta(days=7),
        )
        .limit(3)
    ).all()
    rules = load_function_rules()

    total = sum(counts.values())
    lines = [
        f"BULETIN KAMTIBMAS KELURAHAN {kelurahan.upper()}",
        f"Minggu {week_start:%d %b} - {week_end:%d %b %Y} · Polsek {polsek}",
        "",
    ]
    if total == 0:
        lines.append(
            "Minggu ini tidak ada kejadian pencurian kendaraan, pencurian dengan pemberatan, "
            "maupun pencurian dengan kekerasan yang tercatat di kelurahan kita."
        )
    else:
        lines.append(f"Minggu ini tercatat {total} kejadian di kelurahan kita:")
        for threat in threats:
            if counts.get(threat):
                lines.append(f"• {counts[threat]} {THREAT_LABEL.get(threat, threat.lower())}")
    if alerts:
        lines.append("")
        lines.append("Imbauan yang berlaku:")
        for alert in alerts:
            lines.append(f"• {alert.public_message}")
    if decided:
        lines.append("")
        lines.append("Langkah Polsek yang sudah ditetapkan Pimpinan:")
        for text, function, _status in decided:
            lines.append(f"• {text} ({function})")
    top = max(counts.items(), key=lambda item: item[1])[0] if counts else None
    lines.append("")
    if top:
        rule = rules.for_threat(top)
        lines.append(
            f"Ajakan untuk warga: {rule.action.lower()} bersama Babinkamtibmas; laporkan hal "
            "mencurigakan lewat SIGAP WARGA atau 110."
        )
    else:
        lines.append(
            "Ajakan untuk warga: tetap kunci ganda kendaraan dan saling jaga lingkungan; "
            "laporkan hal mencurigakan lewat SIGAP WARGA atau 110."
        )
    lines.append("")
    lines.append("Dari Polres Metro Jakarta Selatan melalui SIGAP · sigap.awansurya.com")
    figures = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "counts": counts,
        "total": total,
        "alerts": [alert.code for alert in alerts],
        "decided_recommendations": len(decided),
    }
    return "\n".join(lines), figures


def kelurahan_rows(session: Session) -> list[tuple[str, str, str]]:
    return [
        (str(k), str(kc), str(p))
        for k, kc, p in session.execute(
            select(Location.kelurahan, Location.kecamatan, Location.polsek)
            .where(Location.kelurahan.is_not(None))
            .group_by(Location.kelurahan, Location.kecamatan, Location.polsek)
            .order_by(Location.kecamatan, Location.kelurahan)
        ).all()
    ]
