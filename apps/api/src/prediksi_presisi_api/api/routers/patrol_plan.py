"""Rencana patroli tahunan, pencocokannya, dan keputusan Pimpinan atasnya.

```text
GET  /patrol-plan               usulan + keputusan yang berlaku        recommendation:read
GET  /patrol-plan/evaluation    rencana yang berlaku vs kenyataan      evaluation:read
POST /patrol-plan/decisions     setujui / ubah / tolak usulan          commander_decision:approve
GET  /patrol-plan/decisions     riwayat keputusan                      commander_decision:read
```

Human-in-the-loop (CLAUDE.md §13): usulan dihitung sistem, yang berlaku ditentukan
keputusan terakhir Pimpinan. Keputusan menyalin usulan yang dibaca saat memutus
(`plan_snapshot`) dan tidak pernah ditimpa; riwayatnya tetap utuh (CLAUDE.md §29).
Seluruhnya menghormati cakupan wilayah: akun bercakupan Polsek hanya memutus rencana
polseknya, dan keputusannya tercatat dengan cakupan itu.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import PatrolPlanDecision
from ...services import audit, clock, outlook
from ...services import patrol_plan as planning
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from ..errors import ApiError

router = APIRouter(prefix="/patrol-plan", tags=["rencana patroli"])

AUDIT_ACTIONS = {
    "APPROVED": "APPROVE_PATROL_PLAN",
    "MODIFIED": "MODIFY_PATROL_PLAN",
    "REJECTED": "REJECT_PATROL_PLAN",
}
AUDIT_RESOURCE = "patrol_plan"
MAX_HISTORY = 50


def _plan(session: Session, polsek: str | None) -> planning.PatrolPlan:
    try:
        return planning.build_plan(session, polsek)
    except planning.PatrolPlanError as error:
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


def _resource_id(plan: planning.PatrolPlan) -> str:
    return f"{plan.target_year}/{plan.polsek or 'ALL'}"


@router.get("", summary="Usulan slot patroli tahun sasaran beserta keputusan yang berlaku")
def patrol_plan(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("recommendation:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "recommendation:read")
    plan = _plan(session, polsek)
    decision = planning.latest_decision(session, plan.target_year, polsek)
    in_force = planning.apply_decision(plan, decision)
    return {
        **plan.as_dict(),
        "decision": planning.decision_as_dict(decision),
        "in_force": {
            "slots": sum(len(threat.slots) for threat in in_force.threats),
            "keys": [
                {
                    "threat_type": slot.unit.threat_type,
                    "kelurahan": slot.unit.kelurahan,
                    "block_start": slot.unit.block,
                }
                for threat in in_force.threats
                for slot in threat.slots
            ],
        },
        "decision_basis": planning.DECISION_BASIS,
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }


@router.get("/evaluation", summary="Rencana yang berlaku dicocokkan dengan kejadian nyata")
def patrol_plan_evaluation(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("evaluation:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "evaluation:read")
    plan = _plan(session, polsek)
    decision = planning.latest_decision(session, plan.target_year, polsek)
    in_force = planning.apply_decision(plan, decision)
    return {
        **planning.evaluate_plan(session, in_force),
        "decision": planning.decision_as_dict(decision),
        "evaluated_plan": "in_force" if decision is not None else "proposed",
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }


class SlotKey(BaseModel):
    threat_type: str = Field(max_length=50)
    kelurahan: str = Field(max_length=100)
    block_start: int = Field(ge=0, le=23)


class PlanDecisionRequest(BaseModel):
    """Keputusan Pimpinan atas usulan rencana patroli tahun sasaran."""

    decision: str = Field(description="APPROVED, MODIFIED, atau REJECTED")
    reason: str | None = Field(default=None, max_length=2000)
    kept_slots: list[SlotKey] | None = Field(
        default=None,
        description="Slot usulan yang dipertahankan; wajib dan tidak kosong bila MODIFIED.",
    )


@router.post(
    "/decisions",
    status_code=status.HTTP_201_CREATED,
    summary="Menyetujui, mengubah, atau menolak usulan rencana patroli",
)
def decide_patrol_plan(
    payload: PlanDecisionRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("commander_decision:approve"),
) -> dict[str, Any]:
    decision = payload.decision.strip().upper()
    if decision not in AUDIT_ACTIONS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "Keputusan harus APPROVED, MODIFIED, atau REJECTED."
        )
    reason = (payload.reason or "").strip() or None
    if decision == "REJECTED" and reason is None:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Penolakan wajib menyertakan alasan: tanpa alasan, usulan berikutnya tidak "
            "dapat memperbaiki apa pun.",
        )

    polsek = jurisdiction_filter(current, "commander_decision:approve")
    plan = _plan(session, polsek)
    proposed = {
        planning.slot_key(slot.unit.threat_type, slot.unit.kelurahan, slot.unit.block)
        for threat in plan.threats
        for slot in threat.slots
    }
    if not proposed:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "Tidak ada slot yang diusulkan untuk cakupan ini, sehingga tidak ada yang dapat "
            "diputus.",
        )

    kept: list[dict[str, Any]] | None = None
    if decision == "MODIFIED":
        requested = {
            planning.slot_key(row.threat_type, row.kelurahan, row.block_start)
            for row in payload.kept_slots or []
        }
        if not requested:
            raise ApiError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Keputusan MODIFIED wajib menyebut slot yang dipertahankan; tanpa satu pun "
                "slot, gunakan REJECTED.",
            )
        unknown = sorted(requested - proposed)
        if unknown:
            raise ApiError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Slot berikut tidak ada pada usulan dan tidak dapat ditambahkan lewat "
                f"keputusan: {', '.join(f'{t}/{k}/{b:02d}' for t, k, b in unknown)}.",
            )
        if requested == proposed:
            raise ApiError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Seluruh slot dipertahankan: itu persetujuan, gunakan APPROVED.",
            )
        kept = [
            {"threat_type": t, "kelurahan": k, "block_start": b} for t, k, b in sorted(requested)
        ]

    record = PatrolPlanDecision(
        code=planning.next_decision_code(session),
        target_year=plan.target_year,
        scope=polsek,
        plan_version=plan.rules.version,
        plan_snapshot=plan.as_dict(),
        decision=decision,
        reason=reason,
        kept_slots=kept,
        decision_by=current.user.user_id,
    )
    session.add(record)
    audit.record(
        session,
        action=AUDIT_ACTIONS[decision],
        resource_type=AUDIT_RESOURCE,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=_resource_id(plan),
        detail={
            "decision": decision,
            "decision_code": record.code,
            "reason": reason,
            "proposed_slots": len(proposed),
            "kept_slots": None if kept is None else len(kept),
        },
    )
    session.commit()
    session.refresh(record)
    body = planning.decision_as_dict(record) or {}
    return {**body, "decision_basis": planning.DECISION_BASIS}


@router.get("/decisions", summary="Riwayat keputusan atas rencana patroli")
def list_patrol_plan_decisions(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("commander_decision:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "commander_decision:read")
    query = select(PatrolPlanDecision)
    if polsek is not None:
        query = query.where(PatrolPlanDecision.scope == polsek)
    rows = session.scalars(
        query.order_by(PatrolPlanDecision.decision_at.desc(), PatrolPlanDecision.code.desc()).limit(
            MAX_HISTORY
        )
    ).all()
    return {
        "data": [planning.decision_as_dict(row) for row in rows],
        "limit": MAX_HISTORY,
        "decision_basis": planning.DECISION_BASIS,
    }


OUTLOOK_FILENAME = "perkiraan-kerawanan-{month}.docx"


@router.get(
    "/outlook",
    summary="Perkiraan singkat satu bulan ke depan — di mana, jam berapa, rekomendasinya",
)
def monthly_outlook(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("recommendation:read"),
    month: str | None = Query(
        None, pattern=r"^\d{4}-\d{2}$", description="Bulan sasaran YYYY-MM; kosong = bulan depan"
    ),
    format: str = Query("json", pattern="^(json|docx)$"),
) -> Any:
    """Permintaan pemilik proyek 9 Oktober 2026. `format=docx` mengunduh dokumen Word."""
    polsek = jurisdiction_filter(current, "recommendation:read")
    if month:
        year, month_number = int(month[:4]), int(month[5:7])
        if not 1 <= month_number <= 12:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Bulan harus 01-12.")
    else:
        year, month_number = outlook.default_target_month()
    result = outlook.build_outlook(session, year, month_number, polsek)
    audit.record(
        session,
        action="EXPORT_OUTLOOK" if format == "docx" else "VIEW_OUTLOOK",
        resource_type="patrol_plan",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=result["target_month"],
        detail={"format": format, "scope": polsek},
    )
    session.commit()
    if format == "docx":
        filename = OUTLOOK_FILENAME.format(month=result["target_month"])
        return Response(
            content=outlook.render_docx(result),
            media_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return result
