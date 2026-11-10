"""Produk bulanan — Modul 4 "Menyusun dan memvalidasi rekomendasi".

Dua tahap sejak 10 November 2026 (keputusan pemilik proyek 1B, catatan 177):

    Analis menyusun draf — peringkat bulan itu DIBEKUKAN otomatis bila belum —
      lalu memeriksanya dengan informasi lapangan: terima / perbaiki / tolak, dengan alasan,
      dan mengirimkannya ke Pimpinan
      → Pimpinan menetapkan JUMLAH dan KELURAHAN prioritas beserta tindak lanjutnya
      → Fungsi pelaksana / Polsek mencatat waktu, tempat, tindakan, hasil.

Tahap KBO dan validasi Kasat Intelkam (6–10 November 2026) dihapus: keduanya diklik orang
yang sama berturut-turut dan tidak menambah kontrol. Produk yang sudah terlanjur berstatus
KBO_CHECKED / VALIDATED tetap terbaca dan langsung dapat ditetapkan Pimpinan.

Draf tetap disusun dari peringkat yang dibekukan, supaya "peringkat awal model dan daftar
keputusan pimpinan disimpan terpisah" (dokumen mekanisme) — pembekuan kini bagian dari
tombol "Susun", bukan langkah tersendiri. Usulan langkah mengikuti
config/recommendation/function-rules.yaml (PROPOSED) — bukan model bahasa.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..api.analysis import hour_block_label, hour_block_of
from ..models import (
    CrimeIncident,
    Location,
    MonthlyAction,
    MonthlyProduct,
    MonthlyProductItem,
    MonthlyProductStage,
    MonthlyRanking,
    User,
)
from . import clock
from . import monthly_ranking as ranking
from .bulletin import THREAT_LABEL
from .risk_engine import _known_by
from .warning_issuance import load_function_rules


class ProductError(ValueError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


#: Status yang menunggu penetapan Pimpinan. KBO_CHECKED dan VALIDATED hanya tinggalan alur
#: empat tahap (6–10 November 2026); produk lama di status itu tetap dapat ditetapkan.
AWAITING_DECISION = ("ANALYST_REVIEWED", "KBO_CHECKED", "VALIDATED")
STAGE_FOR_STATUS = {
    "DRAFT": "ANALYST",
    "ANALYST_REVIEWED": "PIMPINAN",
    "KBO_CHECKED": "PIMPINAN",
    "VALIDATED": "PIMPINAN",
    "DECIDED": None,
}
BASIS = (
    "Draf disusun sistem dari peringkat bulan sasaran — dibekukan saat draf disusun — dan pola "
    "kejadian pada bulan dasar; usulan langkah dari aturan fungsi (PROPOSED). Analis memeriksa "
    "dengan informasi lapangan; alasan wajib bila ditolak atau diperbaiki. Pimpinan menetapkan "
    "jumlah dan kelurahan prioritas. Fungsi pelaksana dan Polsek mencatat kegiatan. Usulan, "
    "bukan perintah."
)


def _draft_top_n() -> int:
    import yaml

    raw: dict[str, Any] = yaml.safe_load(ranking.CONFIG_FILE.read_text(encoding="utf-8"))
    return int((raw.get("product") or {}).get("draft_top_n", 10))


def _patterns(
    session: Session, frozen: MonthlyRanking, names: list[str]
) -> dict[str, dict[str, Any]]:
    """Pola per kelurahan pada bulan dasar peringkat: jumlah per jenis dan blok jam puncak."""
    query = (
        select(Location.kelurahan, CrimeIncident.incident_type, CrimeIncident.incident_time)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            Location.kelurahan.in_(names),
            CrimeIncident.incident_type.in_(ranking.THREATS),
            CrimeIncident.incident_date >= frozen.basis_from,
            CrimeIncident.incident_date <= frozen.basis_to,
            CrimeIncident.area_pending.is_(False),
            _known_by(frozen.data_cutoff),
        )
    )
    if frozen.scope == "VEHICLE":
        query = query.where(CrimeIncident.vehicle_object.is_(True))
    by_threat: dict[str, Counter[str]] = defaultdict(Counter)
    by_block: dict[str, Counter[int]] = defaultdict(Counter)
    unknown: Counter[str] = Counter()
    for kelurahan, threat, at in session.execute(query).all():
        by_threat[str(kelurahan)][str(threat)] += 1
        if at is None:
            unknown[str(kelurahan)] += 1
        else:
            by_block[str(kelurahan)][hour_block_of(at.hour)] += 1
    out: dict[str, dict[str, Any]] = {}
    for name in names:
        threats = by_threat.get(name, Counter())
        blocks = by_block.get(name, Counter())
        dominant = threats.most_common(1)[0][0] if threats else None
        peak = blocks.most_common(1)[0][0] if blocks else None
        out[name] = {
            "counts": dict(threats),
            "dominant_threat": dominant,
            "peak_block_start": peak,
            "peak_block_label": hour_block_label(peak) if peak is not None else None,
            "unknown_time": unknown.get(name, 0),
        }
    return out


def draft(session: Session, target_month: Any, user_id: Any) -> MonthlyProduct:
    config = ranking.load_config()
    month = ranking.month_start(target_month)
    if session.scalar(select(MonthlyProduct).where(MonthlyProduct.target_month == month)):
        raise ProductError("Produk bulan ini sudah ada.", 409)
    frozen = ranking.stored(session, month, config.default_method, config.default_scope)
    frozen_now = False
    if frozen is None:
        # Pembekuan ikut tombol "Susun" (10 November 2026): satu langkah lebih sedikit, dan
        # yang dibekukan tetap peringkat yang dievaluasi setelah bulan berakhir.
        try:
            computed = ranking.compute(session, month, config.default_method, config.default_scope)
            frozen = ranking.freeze(session, computed, user_id)
        except ranking.RankingError as error:
            raise ProductError(str(error)) from error
        frozen_now = True
    rules = load_function_rules()
    top = frozen.rows[: _draft_top_n()]
    patterns = _patterns(session, frozen, [row.kelurahan for row in top])
    items: list[MonthlyProductItem] = []
    for row in top:
        pattern = patterns[row.kelurahan]
        threat = pattern["dominant_threat"]
        rule = rules.rules.get(threat) if threat else None
        function = rule.function if rule else rules.default_function
        action = rule.action if rule else "Tingkatkan kegiatan preventif"
        where = f"Kelurahan {row.kelurahan} ({row.kecamatan})"
        focus = f" fokus {THREAT_LABEL.get(threat, threat.lower())}" if threat else ""
        when = f" pada blok {pattern['peak_block_label']}" if pattern["peak_block_label"] else ""
        text = (
            f"{action} di {where}{focus}{when}. Dasar: peringkat {row.rank}, perkiraan "
            f"{float(row.predicted_count):.1f} kejadian/bulan, {sum(pattern['counts'].values())} "
            f"kejadian pada {frozen.basis_from.isoformat()[:7]}-{frozen.basis_to.isoformat()[:7]} "
            f"(sumber Pusiknas, batas data {frozen.data_cutoff.isoformat()})."
        )
        items.append(
            MonthlyProductItem(
                rank=row.rank,
                kelurahan=row.kelurahan,
                kecamatan=row.kecamatan,
                polsek=row.polsek,
                predicted_count=row.predicted_count,
                pattern=pattern,
                proposal_text=text,
                proposed_function=function,
            )
        )
    product = MonthlyProduct(
        target_month=month,
        ranking_id=frozen.ranking_id,
        status="DRAFT",
        facts={
            "method": frozen.method,
            "scope": frozen.scope,
            "data_cutoff": frozen.data_cutoff.isoformat(),
            "basis_from": frozen.basis_from.isoformat(),
            "basis_to": frozen.basis_to.isoformat(),
            "pending_count": frozen.pending_count,
            "total_basis": int(sum(float(r.basis.get("basis_total", 0)) for r in frozen.rows)),
            "draft_top_n": len(items),
            "function_rules_status": rules.status,
            "ranking_frozen_by_draft": frozen_now,
        },
        created_by=user_id,
        items=items,
    )
    session.add(product)
    session.flush()
    return product


def load(session: Session, target_month: Any) -> MonthlyProduct:
    month = ranking.month_start(target_month)
    product = session.scalar(
        select(MonthlyProduct)
        .where(MonthlyProduct.target_month == month)
        .options(
            selectinload(MonthlyProduct.items).selectinload(MonthlyProductItem.actions),
            selectinload(MonthlyProduct.stages),
        )
    )
    if product is None:
        raise ProductError("Produk bulan ini belum disusun.", 404)
    return product


def _require(product: MonthlyProduct, *statuses: str) -> None:
    if product.status not in statuses:
        wanted = " / ".join(statuses)
        raise ProductError(f"Produk berstatus {product.status}; tahap ini butuh {wanted}.", 409)


def _stage(
    product: MonthlyProduct,
    stage: str,
    outcome: str,
    user_id: Any,
    reason: str | None,
    note: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    if outcome in ("REJECTED", "REVISED") and not (reason or "").strip():
        raise ProductError("Alasan wajib diisi bila ditolak atau diperbaiki.")
    product.stages.append(
        MonthlyProductStage(
            stage=stage,
            outcome=outcome,
            reason=(reason or "").strip() or None,
            note=(note or "").strip() or None,
            payload=payload or {},
            acted_by=user_id,
            acted_at=clock.citizen_now(),
        )
    )


def analyst_review(
    session: Session,
    product: MonthlyProduct,
    decisions: list[dict[str, Any]],
    note: str | None,
    user_id: Any,
) -> MonthlyProduct:
    _require(product, "DRAFT")
    by_name = {item.kelurahan: item for item in product.items}
    any_revised = False
    for decision in decisions:
        item = by_name.get(str(decision.get("kelurahan", "")))
        if item is None:
            raise ProductError(f"Kelurahan {decision.get('kelurahan')} tidak ada di draf.")
        status = str(decision.get("status", "ACCEPTED")).upper()
        if status not in ("ACCEPTED", "REVISED", "REJECTED"):
            raise ProductError("Status analis harus ACCEPTED, REVISED, atau REJECTED.")
        reason = str(decision.get("reason") or "").strip()
        text = str(decision.get("text") or "").strip()
        if status in ("REVISED", "REJECTED") and not reason:
            raise ProductError(f"Alasan wajib untuk {item.kelurahan} ({status}).")
        if status == "REVISED" and not text:
            raise ProductError(f"Teks perbaikan wajib untuk {item.kelurahan}.")
        item.analyst_status = status
        item.analyst_text = text or None
        item.analyst_reason = reason or None
        any_revised = any_revised or status != "ACCEPTED"
    for item in product.items:
        if item.analyst_status is None:
            item.analyst_status = "ACCEPTED"
    _stage(
        product,
        "ANALYST",
        "REVISED" if any_revised else "ACCEPTED",
        user_id,
        reason="diperiksa dengan informasi lapangan" if any_revised else None,
        note=note,
        payload={"decided": len(decisions)},
    )
    product.status = "ANALYST_REVIEWED"
    session.flush()
    return product


def decide(
    session: Session,
    product: MonthlyProduct,
    selected: list[dict[str, Any]],
    reason: str | None,
    user_id: Any,
) -> MonthlyProduct:
    _require(product, *AWAITING_DECISION)
    if not selected:
        raise ProductError("Pilih sedikitnya satu kelurahan prioritas.")
    by_name = {item.kelurahan: item for item in product.items}
    chosen: list[str] = []
    for entry in selected:
        name = str(entry.get("kelurahan", ""))
        item = by_name.get(name)
        if item is None:
            raise ProductError(f"Kelurahan {name} tidak ada di produk.")
        if item.analyst_status == "REJECTED":
            raise ProductError(f"Kelurahan {name} ditolak analis; tidak dapat dipilih.")
        item.selected = True
        item.decided_action = str(entry.get("action") or "").strip() or (
            item.analyst_text or item.proposal_text
        )
        chosen.append(name)
    for item in product.items:
        if item.kelurahan not in chosen:
            item.selected = False
            item.decided_action = None
    product.priority_count = len(chosen)
    product.decided_at = clock.citizen_now()
    _stage(product, "PIMPINAN", "DECIDED", user_id, None, note=reason, payload={"selected": chosen})
    product.status = "DECIDED"
    session.flush()
    return product


def record_action(
    session: Session, product: MonthlyProduct, kelurahan: str, user: User, body: dict[str, Any]
) -> MonthlyAction:
    _require(product, "DECIDED")
    item = next((i for i in product.items if i.kelurahan == kelurahan), None)
    if item is None or not item.selected:
        raise ProductError("Kelurahan ini bukan prioritas yang ditetapkan.", 404)
    if user.polsek and item.polsek != user.polsek:
        raise ProductError("Kelurahan ini di luar wilayah Anda.", 404)
    acted_at = body.get("acted_at")
    if not isinstance(acted_at, datetime):
        raise ProductError("Waktu kegiatan wajib.")
    row = MonthlyAction(
        recorded_by=user.user_id,
        unit=str(body.get("unit") or user.function or user.polsek or "").strip()[:100] or "—",
        acted_at=acted_at,
        place=str(body.get("place") or "").strip()[:200],
        action=str(body.get("action") or "").strip(),
        result=(str(body.get("result") or "").strip() or None),
    )
    if not row.place or not row.action:
        raise ProductError("Tempat dan tindakan wajib diisi.")
    # Lewat relasi, bukan item_id mentah: koleksi `item.actions` yang sudah dimuat ikut
    # bertambah, sehingga pembaca pada session yang sama melihatnya.
    item.actions.append(row)
    session.flush()
    return row


def as_dict(product: MonthlyProduct) -> dict[str, Any]:
    return {
        "product_id": str(product.product_id),
        "target_month": product.target_month.isoformat()[:7],
        "status": product.status,
        "next_stage": STAGE_FOR_STATUS.get(product.status),
        "awaiting_decision": product.status in AWAITING_DECISION,
        "facts": product.facts,
        "priority_count": product.priority_count,
        "decided_at": product.decided_at,
        "items": [
            {
                "rank": item.rank,
                "kelurahan": item.kelurahan,
                "kecamatan": item.kecamatan,
                "polsek": item.polsek,
                "predicted_count": float(item.predicted_count),
                "pattern": item.pattern,
                "proposal_text": item.proposal_text,
                "proposed_function": item.proposed_function,
                "analyst_status": item.analyst_status,
                "analyst_text": item.analyst_text,
                "analyst_reason": item.analyst_reason,
                "selected": item.selected,
                "decided_action": item.decided_action,
                "actions": [
                    {
                        "unit": a.unit,
                        "acted_at": a.acted_at,
                        "place": a.place,
                        "action": a.action,
                        "result": a.result,
                    }
                    for a in item.actions
                ],
            }
            for item in product.items
        ],
        "stages": [
            {
                "stage": s.stage,
                "outcome": s.outcome,
                "reason": s.reason,
                "note": s.note,
                "payload": s.payload,
                "acted_at": s.acted_at,
            }
            for s in product.stages
        ],
        "basis": BASIS,
    }


def months(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            MonthlyProduct.target_month, MonthlyProduct.status, MonthlyProduct.priority_count
        ).order_by(MonthlyProduct.target_month.desc())
    ).all()
    return [
        {"target_month": m.isoformat()[:7], "status": status, "priority_count": count}
        for m, status, count in rows
    ]
