"""Rencana patroli tahunan: dari pola tahun lalu, usulan kelurahan × blok jam × jenis.

Permintaan pemilik proyek 4 Oktober 2026. Aplikasi berdiri di awal 2026 dan hanya melihat
kejadian sampai 2025 (`services/visibility.py`). Dari pola itu sistem menyusun USULAN
kepada Pimpinan: di kelurahan mana dan pada blok jam berapa patroli dilakukan untuk tiap
jenis ancaman sepanjang 2026. Usulan itu lalu DICOCOKKAN dengan kejadian nyata 2026 — satu-
satunya pembaca data 2026 selain evaluasi mundur.

```text
POLA 2025 (kelurahan x blok 3 jam x jenis)
      ↓  peringkat, batas slot, batas minimum   (config/patrol/plan-rules.yaml)
USULAN SLOT PATROLI 2026               — usulan, bukan perintah
      ↓  dibaca Pimpinan
KEJADIAN NYATA 2026                    — hanya untuk pencocokan
      ↓
KEMIRIPAN: pola jam · pola wilayah · ketepatan slot · cakupan kejadian
```

TIGA HAL YANG MENJAGA KEJUJURANNYA

1. **Usulan tidak disimpan.** Ia dihitung dari data setiap kali dibuka dan menyebut versi
   aturannya. Menyimpannya berarti harus menjelaskan mengapa usulan tersimpan berbeda dari
   data yang sekarang — tanpa ada yang bertanya.
2. **Setiap slot membawa angkanya.** "Kelurahan X, 18.00-21.00" diusulkan karena N kejadian
   jenis itu terjadi di sana pada blok itu sepanjang tahun dasar, M% dari seluruh kejadian
   jenis itu yang jamnya tercatat. Tidak ada skor yang tidak dapat dihitung ulang dengan
   tangan.
3. **Kemiripan dinyatakan sebagai empat angka yang masing-masing jelas definisinya**, bukan
   satu persen gabungan — sebab "mirip 73%" tanpa definisi tidak dapat dipertanggung-
   jawabkan di depan penguji. Keempatnya berstatus PROPOSED sampai pemilik proyek
   menetapkan mana yang menjadi ukuran resmi.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import yaml
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from ..api.analysis import HOUR_BLOCK_STARTS, hour_block_label, hour_block_of
from ..models import CrimeIncident, Location, PatrolPlanDecision
from ..seeding.paths import REPO_ROOT
from . import risk_engine as risk
from . import visibility

PLAN_RULES_FILE = REPO_ROOT / "config" / "patrol" / "plan-rules.yaml"

PLAN_BASIS = (
    "Slot = kelurahan x blok 3 jam x jenis. Untuk tiap jenis, slot diperingkat menurut "
    "jumlah kejadian pada tahun dasar yang jamnya tercatat; yang diusulkan adalah slot "
    "teratas sebanyak max_slots_per_threat dengan kejadian >= minimum_incidents "
    "(config/patrol/plan-rules.yaml). Kejadian tanpa jam atau tanpa kelurahan tidak masuk "
    "slot mana pun dan disebut terpisah. Ini USULAN kepada Pimpinan, bukan perintah."
)

SIMILARITY_BASIS = (
    "Kemiripan pola jam = jumlah atas delapan blok dari min(porsi blok pada tahun dasar, "
    "porsi blok pada tahun sasaran); kemiripan pola wilayah dihitung sama atas kelurahan. "
    "Keduanya 100% bila kedua tahun berbagi sebaran yang persis sama. Ketepatan slot = "
    "porsi slot usulan yang benar-benar mengalami kejadian jenis itu pada tahun sasaran. "
    "Cakupan kejadian = porsi kejadian tahun sasaran (berjam, berkelurahan) yang jatuh di "
    "slot usulan. Status PROPOSED: ukuran resmi menunggu penetapan pemilik proyek."
)


class PatrolPlanError(Exception):
    """Konfigurasi atau data tidak memungkinkan penyusunan rencana."""


@dataclass(frozen=True)
class PlanRules:
    status: str
    version: str
    basis_months: int
    max_slots_per_threat: int
    minimum_incidents: int


def load_rules() -> PlanRules:
    if not PLAN_RULES_FILE.exists():
        message = "config/patrol/plan-rules.yaml tidak ditemukan"
        raise PatrolPlanError(message)
    raw: dict[str, Any] = yaml.safe_load(PLAN_RULES_FILE.read_text(encoding="utf-8"))
    rules = PlanRules(
        status=str(raw.get("status", "UNKNOWN")),
        version=str(raw.get("version", "rencana-patroli-v1")),
        basis_months=int(raw.get("basis_months", 12)),
        max_slots_per_threat=int(raw.get("max_slots_per_threat", 15)),
        minimum_incidents=int(raw.get("minimum_incidents", 1)),
    )
    if rules.basis_months < 1 or rules.max_slots_per_threat < 1 or rules.minimum_incidents < 1:
        message = "config/patrol/plan-rules.yaml: seluruh parameter harus >= 1"
        raise PatrolPlanError(message)
    return rules


# ---------------------------------------------------------------------------
# Bahan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    """Satu sel usulan: kelurahan pada kecamatan/polsek tertentu, blok jam, jenis."""

    threat_type: str
    polsek: str
    kecamatan: str
    kelurahan: str
    block: int


@dataclass
class Observation:
    """Cacah kejadian satu tahun, siap dibandingkan."""

    year_from: date
    year_to: date
    observed_to: date | None
    by_unit: dict[Unit, int]
    by_block: dict[tuple[str, int], int]
    by_kelurahan: dict[tuple[str, str], int]
    total: dict[str, int]
    with_hour: dict[str, int]
    unknown_time: dict[str, int]
    unknown_kelurahan: dict[str, int]


def _scoped(query: Any, polsek: str | None) -> Any:
    return query if polsek is None else query.where(Location.polsek == polsek)


def observe(
    session: Session,
    start: date,
    end: date,
    threats: tuple[str, ...],
    polsek: str | None,
    *,
    beyond_display: bool = False,
) -> Observation:
    """Mengumpulkan cacah kejadian pada [start, end] per unit, blok, kelurahan, dan jenis."""
    hour = cast(func.extract("hour", CrimeIncident.incident_time), Integer)
    detail = _scoped(
        select(
            CrimeIncident.incident_type,
            Location.polsek,
            Location.kecamatan,
            Location.kelurahan,
            hour,
            func.count(),
        )
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            CrimeIncident.incident_date >= start,
            CrimeIncident.incident_date <= end,
            CrimeIncident.incident_type.in_(threats),
            CrimeIncident.time_known.is_(True),
        )
        .group_by(
            CrimeIncident.incident_type,
            Location.polsek,
            Location.kecamatan,
            Location.kelurahan,
            hour,
        ),
        polsek,
    )
    totals = _scoped(
        select(
            CrimeIncident.incident_type,
            func.count(),
            func.sum(cast(CrimeIncident.time_known, Integer)),
            func.sum(cast(Location.kelurahan.is_(None), Integer)),
            func.max(CrimeIncident.incident_date),
        )
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            CrimeIncident.incident_date >= start,
            CrimeIncident.incident_date <= end,
            CrimeIncident.incident_type.in_(threats),
        )
        .group_by(CrimeIncident.incident_type),
        polsek,
    )
    if beyond_display:
        detail = visibility.all_incidents(detail)
        totals = visibility.all_incidents(totals)

    by_unit: dict[Unit, int] = defaultdict(int)
    by_block: dict[tuple[str, int], int] = defaultdict(int)
    by_kelurahan: dict[tuple[str, str], int] = defaultdict(int)
    unknown_kelurahan_with_hour: dict[str, int] = defaultdict(int)
    for threat, unit_polsek, kecamatan, kelurahan, raw_hour, count in session.execute(detail).all():
        block = hour_block_of(int(raw_hour))
        by_block[(str(threat), block)] += int(count)
        if kelurahan is None:
            unknown_kelurahan_with_hour[str(threat)] += int(count)
            continue
        by_kelurahan[(str(threat), str(kelurahan))] += int(count)
        by_unit[Unit(str(threat), str(unit_polsek), str(kecamatan), str(kelurahan), block)] += int(
            count
        )

    total: dict[str, int] = {}
    with_hour: dict[str, int] = {}
    unknown_time: dict[str, int] = {}
    unknown_kelurahan: dict[str, int] = {}
    observed_to: date | None = None
    for threat, count, known, no_kelurahan, last in session.execute(totals).all():
        total[str(threat)] = int(count)
        with_hour[str(threat)] = int(known or 0)
        unknown_time[str(threat)] = int(count) - int(known or 0)
        unknown_kelurahan[str(threat)] = int(no_kelurahan or 0)
        if last is not None and (observed_to is None or last > observed_to):
            observed_to = last

    return Observation(
        year_from=start,
        year_to=end,
        observed_to=observed_to,
        by_unit=dict(by_unit),
        by_block=dict(by_block),
        by_kelurahan=dict(by_kelurahan),
        total=total,
        with_hour=with_hour,
        unknown_time=unknown_time,
        unknown_kelurahan=unknown_kelurahan,
    )


# ---------------------------------------------------------------------------
# Usulan
# ---------------------------------------------------------------------------


@dataclass
class Slot:
    unit: Unit
    rank: int
    incidents: int
    share_percent: float
    cumulative_share_percent: float

    def as_dict(self) -> dict[str, Any]:
        unit = self.unit
        return {
            "rank": self.rank,
            "threat_type": unit.threat_type,
            "polsek": unit.polsek,
            "kecamatan": unit.kecamatan,
            "kelurahan": unit.kelurahan,
            "block_start": unit.block,
            "block_label": hour_block_label(unit.block),
            "incidents": self.incidents,
            "share_percent": self.share_percent,
            "cumulative_share_percent": self.cumulative_share_percent,
            "why": (
                f"{self.incidents} kejadian {unit.threat_type} di Kelurahan {unit.kelurahan} "
                f"({unit.kecamatan}) pada {hour_block_label(unit.block)} sepanjang tahun dasar — "
                f"{self.share_percent}% dari seluruh {unit.threat_type} yang jamnya tercatat."
            ),
        }


@dataclass
class ThreatPlan:
    threat_type: str
    slots: list[Slot]
    basis_total: int
    basis_with_hour: int
    basis_unknown_time: int
    basis_unknown_kelurahan: int

    @property
    def covered_share_percent(self) -> float:
        return self.slots[-1].cumulative_share_percent if self.slots else 0.0


@dataclass
class PatrolPlan:
    rules: PlanRules
    basis_from: date
    basis_to: date
    target_year: int
    polsek: str | None
    threats: list[ThreatPlan] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.rules.version,
            "status": self.rules.status,
            "basis_from": self.basis_from.isoformat(),
            "basis_to": self.basis_to.isoformat(),
            "target_year": self.target_year,
            "scope": self.polsek,
            "rules": {
                "basis_months": self.rules.basis_months,
                "max_slots_per_threat": self.rules.max_slots_per_threat,
                "minimum_incidents": self.rules.minimum_incidents,
            },
            "threats": [
                {
                    "threat_type": plan.threat_type,
                    "basis_incidents": plan.basis_total,
                    "basis_with_hour": plan.basis_with_hour,
                    "basis_unknown_time": plan.basis_unknown_time,
                    "basis_unknown_kelurahan": plan.basis_unknown_kelurahan,
                    "slots": [slot.as_dict() for slot in plan.slots],
                    "covered_share_percent": plan.covered_share_percent,
                }
                for plan in self.threats
            ],
            "plan_basis": PLAN_BASIS,
        }


def _basis_window(cutoff: date, months: int) -> tuple[date, date]:
    """`months` bulan kalender yang berakhir pada `cutoff`, kedua ujung inklusif."""
    index = cutoff.year * 12 + (cutoff.month - 1) - months
    year, month = divmod(index, 12)
    try:
        start = date(year, month + 1, cutoff.day)
    except ValueError:
        start = date(year + (month + 1) // 12, (month + 1) % 12 + 1, 1) - timedelta(days=1)
    return start + timedelta(days=1), cutoff


def _cutoff(session: Session) -> date:
    cutoff = visibility.display_cutoff()
    if cutoff is not None:
        return cutoff
    last = session.scalar(select(func.max(CrimeIncident.incident_date)))
    if last is None:
        message = "tidak ada satu pun kejadian untuk dijadikan dasar rencana"
        raise PatrolPlanError(message)
    return date(last.year, 12, 31)


def _threats() -> tuple[str, ...]:
    profile = risk.load_weights().active.profiles.get(risk.PROFILE_HISTORICAL)
    return () if profile is None else profile.applies_to


def build_plan(session: Session, polsek: str | None = None) -> PatrolPlan:
    rules = load_rules()
    cutoff = _cutoff(session)
    basis_from, basis_to = _basis_window(cutoff, rules.basis_months)
    threats = _threats()
    observation = observe(session, basis_from, basis_to, threats, polsek)

    plan = PatrolPlan(
        rules=rules,
        basis_from=basis_from,
        basis_to=basis_to,
        target_year=cutoff.year + 1,
        polsek=polsek,
    )
    for threat in threats:
        candidates = sorted(
            (
                (unit, count)
                for unit, count in observation.by_unit.items()
                if unit.threat_type == threat
            ),
            key=lambda item: (-item[1], item[0].kecamatan, item[0].kelurahan, item[0].block),
        )
        with_hour = observation.with_hour.get(threat, 0)
        slots: list[Slot] = []
        cumulative = 0
        for unit, count in candidates:
            if count < rules.minimum_incidents or len(slots) >= rules.max_slots_per_threat:
                break
            cumulative += count
            slots.append(
                Slot(
                    unit=unit,
                    rank=len(slots) + 1,
                    incidents=count,
                    share_percent=round(100 * count / with_hour, 1) if with_hour else 0.0,
                    cumulative_share_percent=(
                        round(100 * cumulative / with_hour, 1) if with_hour else 0.0
                    ),
                )
            )
        plan.threats.append(
            ThreatPlan(
                threat_type=threat,
                slots=slots,
                basis_total=observation.total.get(threat, 0),
                basis_with_hour=with_hour,
                basis_unknown_time=observation.unknown_time.get(threat, 0),
                basis_unknown_kelurahan=observation.unknown_kelurahan.get(threat, 0),
            )
        )
    return plan


# ---------------------------------------------------------------------------
# Pencocokan dengan tahun sasaran
# ---------------------------------------------------------------------------


def _overlap(left: dict[Any, int], right: dict[Any, int]) -> float | None:
    """Σ min(porsi kiri, porsi kanan) x 100 — 100 bila sebarannya identik."""
    left_total = sum(left.values())
    right_total = sum(right.values())
    if left_total == 0 or right_total == 0:
        return None
    keys = set(left) | set(right)
    return round(
        100 * sum(min(left.get(k, 0) / left_total, right.get(k, 0) / right_total) for k in keys),
        1,
    )


def evaluate_plan(session: Session, plan: PatrolPlan) -> dict[str, Any]:
    """Mencocokkan usulan dengan kejadian nyata tahun sasaran (membaca di luar batas tampilan)."""
    threats = tuple(item.threat_type for item in plan.threats)
    target_from = date(plan.target_year, 1, 1)
    target_to = date(plan.target_year, 12, 31)
    basis = observe(session, plan.basis_from, plan.basis_to, threats, plan.polsek)
    actual = observe(session, target_from, target_to, threats, plan.polsek, beyond_display=True)

    per_threat: list[dict[str, Any]] = []
    for threat_plan in plan.threats:
        threat = threat_plan.threat_type
        basis_blocks = {
            block: count for (kind, block), count in basis.by_block.items() if kind == threat
        }
        actual_blocks = {
            block: count for (kind, block), count in actual.by_block.items() if kind == threat
        }
        basis_areas = {
            kel: count for (kind, kel), count in basis.by_kelurahan.items() if kind == threat
        }
        actual_areas = {
            kel: count for (kind, kel), count in actual.by_kelurahan.items() if kind == threat
        }

        slot_rows: list[dict[str, Any]] = []
        hit_slots = 0
        covered = 0
        for slot in threat_plan.slots:
            actual_count = actual.by_unit.get(slot.unit, 0)
            hit_slots += 1 if actual_count > 0 else 0
            covered += actual_count
            slot_rows.append(
                {**slot.as_dict(), "actual_incidents": actual_count, "hit": actual_count > 0}
            )
        evaluable = sum(
            count for unit, count in actual.by_unit.items() if unit.threat_type == threat
        )
        slots_total = len(threat_plan.slots)

        per_threat.append(
            {
                "threat_type": threat,
                "slots": slots_total,
                "slots_hit": hit_slots,
                "slot_hit_rate_percent": (
                    round(100 * hit_slots / slots_total, 1) if slots_total else None
                ),
                "actual_incidents": actual.total.get(threat, 0),
                "actual_evaluable": evaluable,
                "actual_unknown_time": actual.unknown_time.get(threat, 0),
                "actual_unknown_kelurahan": actual.unknown_kelurahan.get(threat, 0),
                "covered_incidents": covered,
                "coverage_percent": round(100 * covered / evaluable, 1) if evaluable else None,
                "hour_similarity_percent": _overlap(basis_blocks, actual_blocks),
                "area_similarity_percent": _overlap(basis_areas, actual_areas),
                "hour_profile": [
                    {
                        "block_start": start,
                        "block_label": hour_block_label(start),
                        "basis_incidents": basis_blocks.get(start, 0),
                        "actual_incidents": actual_blocks.get(start, 0),
                    }
                    for start in HOUR_BLOCK_STARTS
                ],
                "slot_results": slot_rows,
            }
        )

    total_slots = sum(row["slots"] for row in per_threat)
    total_hits = sum(row["slots_hit"] for row in per_threat)
    total_evaluable = sum(row["actual_evaluable"] for row in per_threat)
    total_covered = sum(row["covered_incidents"] for row in per_threat)
    all_basis_blocks: dict[int, int] = defaultdict(int)
    all_actual_blocks: dict[int, int] = defaultdict(int)
    for (_kind, block), count in basis.by_block.items():
        all_basis_blocks[block] += count
    for (_kind, block), count in actual.by_block.items():
        all_actual_blocks[block] += count
    all_basis_areas: dict[str, int] = defaultdict(int)
    all_actual_areas: dict[str, int] = defaultdict(int)
    for (_kind, kel), count in basis.by_kelurahan.items():
        all_basis_areas[kel] += count
    for (_kind, kel), count in actual.by_kelurahan.items():
        all_actual_areas[kel] += count

    return {
        "version": plan.rules.version,
        "status": "PROPOSED",
        "target_year": plan.target_year,
        "target_observed_from": target_from.isoformat(),
        "target_observed_to": (
            actual.observed_to.isoformat() if actual.observed_to is not None else None
        ),
        "scope": plan.polsek,
        "overall": {
            "slots": total_slots,
            "slots_hit": total_hits,
            "slot_hit_rate_percent": round(100 * total_hits / total_slots, 1)
            if total_slots
            else None,
            "actual_evaluable": total_evaluable,
            "covered_incidents": total_covered,
            "coverage_percent": round(100 * total_covered / total_evaluable, 1)
            if total_evaluable
            else None,
            "hour_similarity_percent": _overlap(dict(all_basis_blocks), dict(all_actual_blocks)),
            "area_similarity_percent": _overlap(dict(all_basis_areas), dict(all_actual_areas)),
        },
        "per_threat": per_threat,
        "similarity_basis": SIMILARITY_BASIS,
        "partial_year_basis": (
            "Tahun sasaran dibandingkan sejauh datanya ada (target_observed_to). Cakupan dan "
            "ketepatan slot dihitung atas kejadian yang sudah tercatat, bukan setahun penuh."
        ),
    }


# ---------------------------------------------------------------------------
# Keputusan Pimpinan
# ---------------------------------------------------------------------------

DECISION_BASIS = (
    "Keputusan menyalin usulan yang dibaca saat memutus (plan_snapshot) dan tidak ditimpa; "
    "yang berlaku adalah keputusan TERAKHIR untuk tahun sasaran dan cakupan yang sama. "
    "APPROVED: seluruh slot usulan berlaku. MODIFIED: hanya slot yang dipertahankan "
    "(kept_slots) berlaku; slot di luar usulan tidak dapat ditambahkan di sini. REJECTED: "
    "tidak ada slot yang berlaku, alasannya wajib. Pencocokan dengan kejadian nyata "
    "dihitung atas slot yang berlaku."
)


def slot_key(threat_type: str, kelurahan: str, block_start: int) -> tuple[str, str, int]:
    return (threat_type.upper(), kelurahan, int(block_start))


def latest_decision(
    session: Session, target_year: int, polsek: str | None
) -> PatrolPlanDecision | None:
    """Keputusan yang berlaku: yang terakhir untuk tahun sasaran dan cakupan ini."""
    query = select(PatrolPlanDecision).where(PatrolPlanDecision.target_year == target_year)
    query = (
        query.where(PatrolPlanDecision.scope.is_(None))
        if polsek is None
        else query.where(PatrolPlanDecision.scope == polsek)
    )
    return session.scalar(
        query.order_by(PatrolPlanDecision.decision_at.desc(), PatrolPlanDecision.code.desc())
    )


def decision_as_dict(decision: PatrolPlanDecision | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    return {
        "code": decision.code,
        "decision": decision.decision,
        "reason": decision.reason,
        "kept_slots": decision.kept_slots,
        "plan_version": decision.plan_version,
        "target_year": decision.target_year,
        "scope": decision.scope,
        "decided_by": decision.decided_by.full_name or decision.decided_by.username,
        "decided_at": decision.decision_at,
        "proposed_slots": sum(
            len(threat.get("slots", [])) for threat in decision.plan_snapshot.get("threats", [])
        ),
        "slots_in_force": _slots_in_force_count(decision),
    }


def _slots_in_force_count(decision: PatrolPlanDecision) -> int:
    if decision.decision == "REJECTED":
        return 0
    if decision.decision == "MODIFIED":
        return len(decision.kept_slots or [])
    return sum(len(threat.get("slots", [])) for threat in decision.plan_snapshot.get("threats", []))


def apply_decision(plan: PatrolPlan, decision: PatrolPlanDecision | None) -> PatrolPlan:
    """Rencana yang BERLAKU: usulan disaring menurut keputusan terakhir.

    Tanpa keputusan, yang berlaku adalah usulan apa adanya — dan responsnya menyatakan
    bahwa ia belum diputus. Slot yang dipertahankan dicocokkan menurut kuncinya
    (jenis, kelurahan, blok), bukan menurut peringkat: peringkat dapat bergeser bila
    data dasar berubah, kuncinya tidak.
    """
    if decision is None or decision.decision == "APPROVED":
        return plan
    kept: set[tuple[str, str, int]] = set()
    if decision.decision == "MODIFIED":
        kept = {
            slot_key(str(row["threat_type"]), str(row["kelurahan"]), int(row["block_start"]))
            for row in decision.kept_slots or []
        }
    filtered = PatrolPlan(
        rules=plan.rules,
        basis_from=plan.basis_from,
        basis_to=plan.basis_to,
        target_year=plan.target_year,
        polsek=plan.polsek,
    )
    for threat in plan.threats:
        slots = [
            slot
            for slot in threat.slots
            if slot_key(slot.unit.threat_type, slot.unit.kelurahan, slot.unit.block) in kept
        ]
        filtered.threats.append(
            ThreatPlan(
                threat_type=threat.threat_type,
                slots=slots,
                basis_total=threat.basis_total,
                basis_with_hour=threat.basis_with_hour,
                basis_unknown_time=threat.basis_unknown_time,
                basis_unknown_kelurahan=threat.basis_unknown_kelurahan,
            )
        )
    return filtered


def next_decision_code(session: Session) -> str:
    latest = session.scalar(
        select(PatrolPlanDecision.code)
        .where(PatrolPlanDecision.code.regexp_match("^PPD-[0-9]+$"))
        .order_by(func.length(PatrolPlanDecision.code).desc(), PatrolPlanDecision.code.desc())
    )
    number = 1 if latest is None else int(latest.rsplit("-", 1)[-1]) + 1
    return f"PPD-{number:04d}"
