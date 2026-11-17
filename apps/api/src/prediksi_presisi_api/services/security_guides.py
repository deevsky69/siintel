"""Panduan pengamanan untuk warga — kos, parkir, gedung, RT/RW (naskah Taskap 4.7 f).

Teks panduan ada di config/recommendation/security-guides.yaml (PROPOSED). Di samping tiap
panduan ditampilkan POLA dari data kejadian 12 bulan terakhir pada jenis tempat itu: jumlah
kejadian 3C, porsinya, modus terbanyak, dan rentang jam terbanyak — supaya "berdasarkan pola
kejadian" benar-benar berasal dari data, bukan kalimat tempelan (CLAUDE.md §27).

Pola dihitung se-Polres dan hanya berupa agregat: tidak ada alamat, tanggal, atau identitas.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..api.analysis import hour_block_label, hour_block_of
from ..models import CrimeIncident
from ..seeding.paths import REPO_ROOT
from . import clock, config_cache, visibility
from .monthly_ranking import THREATS

GUIDES_FILE = REPO_ROOT / "config" / "recommendation" / "security-guides.yaml"
PATTERN_DAYS = 365
TOP_MODUS = 2

BASIS = (
    "Panduan umum pengamanan untuk warga dan pengelola (rancangan, belum ditinjau Binmas). "
    "Pola di samping tiap panduan dihitung dari kejadian curat, curas, dan curanmor 12 bulan "
    "terakhir pada jenis tempat itu di wilayah hukum Polres — agregat, tanpa alamat maupun "
    "identitas."
)


def load_guides() -> dict[str, Any]:
    raw: dict[str, Any] = config_cache.load_yaml(GUIDES_FILE) or {}
    return raw


def _pattern(session: Session, location_types: list[str], total: int) -> dict[str, Any]:
    until = visibility.display_cutoff() or clock.reference_now().astimezone(clock.JAKARTA).date()
    since = until - timedelta(days=PATTERN_DAYS - 1)
    rows = session.execute(
        select(CrimeIncident.modus, CrimeIncident.incident_time).where(
            CrimeIncident.incident_type.in_(THREATS),
            CrimeIncident.location_type.in_(location_types),
            CrimeIncident.incident_date >= since,
            CrimeIncident.incident_date <= until,
        )
    ).all()
    modus: Counter[str] = Counter(str(m) for m, _ in rows if m)
    blocks: Counter[int] = Counter(hour_block_of(at.hour) for _, at in rows if at is not None)
    peak = blocks.most_common(1)[0] if blocks else None
    return {
        "incidents": len(rows),
        "share_pct": round(len(rows) / total * 100, 1) if total else None,
        "top_modus": [
            {"modus": name, "count": count} for name, count in modus.most_common(TOP_MODUS)
        ],
        "peak_block": hour_block_label(peak[0]) if peak else None,
        "peak_block_count": peak[1] if peak else 0,
        "with_time": sum(blocks.values()),
        "from": since,
        "to": until,
    }


def guides(session: Session) -> dict[str, Any]:
    raw = load_guides()
    until = visibility.display_cutoff() or clock.reference_now().astimezone(clock.JAKARTA).date()
    since = until - timedelta(days=PATTERN_DAYS - 1)
    total = int(
        session.scalar(
            select(func.count())
            .select_from(CrimeIncident)
            .where(
                CrimeIncident.incident_type.in_(THREATS),
                CrimeIncident.incident_date >= since,
                CrimeIncident.incident_date <= until,
            )
        )
        or 0
    )
    result: dict[str, Any] = {
        "status": str(raw.get("status", "UNKNOWN")),
        "closing": str(raw.get("closing", "")),
        "data": [
            {
                "id": str(item["id"]),
                "title": str(item["title"]),
                "audience": str(item.get("audience", "")),
                "steps": [str(step) for step in item.get("steps", [])],
                "pattern": _pattern(
                    session, [str(t) for t in item.get("location_types", [])], total
                ),
            }
            for item in raw.get("guides", [])
        ],
        "basis": BASIS,
    }
    for guide in result["data"]:
        guide["text"] = render_text(guide, result["closing"])
    return result


def render_text(guide: dict[str, Any], closing: str) -> str:
    """Satu panduan sebagai pesan teks (bot)."""
    lines = [f"*Panduan pengamanan — {guide['title']}*", f"Untuk: {guide['audience']}", ""]
    lines += [f"{number}. {step}" for number, step in enumerate(guide["steps"], start=1)]
    pattern = guide["pattern"]
    if pattern["incidents"]:
        note = f"Setahun terakhir tercatat {pattern['incidents']} kejadian di jenis tempat ini"
        if pattern["peak_block"]:
            note += f", paling sering pukul {pattern['peak_block']}"
        lines += ["", note + "."]
    if closing:
        lines += ["", closing]
    return "\n".join(lines)
