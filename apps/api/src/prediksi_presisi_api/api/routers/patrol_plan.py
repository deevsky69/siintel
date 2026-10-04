"""Rencana patroli tahunan dan pencocokannya (permintaan pemilik proyek 4 Oktober 2026).

```text
GET /patrol-plan              usulan slot patroli tahun sasaran      recommendation:read
GET /patrol-plan/evaluation   usulan dicocokkan kejadian nyata       evaluation:read
```

Keduanya menghormati cakupan wilayah: akun Polsek hanya menerima usulan dan pencocokan
untuk polseknya. Usulan tidak disimpan; ia dihitung dari data saat diminta
(`services/patrol_plan.py`).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...services import clock
from ...services import patrol_plan as planning
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from ..errors import ApiError

router = APIRouter(prefix="/patrol-plan", tags=["rencana patroli"])


def _plan(session: Session, polsek: str | None) -> planning.PatrolPlan:
    try:
        return planning.build_plan(session, polsek)
    except planning.PatrolPlanError as error:
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@router.get("", summary="Usulan slot patroli tahun sasaran dari pola tahun dasar")
def patrol_plan(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("recommendation:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "recommendation:read")
    plan = _plan(session, polsek)
    return {
        **plan.as_dict(),
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }


@router.get("/evaluation", summary="Usulan dicocokkan dengan kejadian nyata tahun sasaran")
def patrol_plan_evaluation(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("evaluation:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "evaluation:read")
    plan = _plan(session, polsek)
    return {
        **planning.evaluate_plan(session, plan),
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }
