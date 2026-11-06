"""Peringkat bulanan kelurahan (Modul 2–3 mekanisme).

`GET /rankings` mengembalikan peringkat yang sudah dibekukan bila ada; bila belum, hasil
hitungan saat ini ditandai `frozen: false`. Membekukan hanya `ranking:manage`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ...services import audit
from ...services import monthly_ranking as ranking
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError

router = APIRouter(tags=["peringkat bulanan"])


class FreezeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    method: str | None = None
    scope: str | None = None
    data_cutoff: date | None = None


def _month(text: str | None, session: Session) -> date:
    if not text:
        return ranking.suggested_target_month(session)
    try:
        return ranking.parse_month(text)
    except ranking.RankingError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.get("/rankings/options", summary="Pilihan metode, cakupan, dan bulan yang disarankan")
def options(
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("ranking:read"),
) -> dict[str, Any]:
    config = ranking.load_config()
    return {
        "version": config.version,
        "status": config.status,
        "default_method": config.default_method,
        "methods": [
            {"value": key, "label": value["label"], "available": key != "MODEL"}
            for key, value in config.methods.items()
        ],
        "scopes": list(config.scopes),
        "default_scope": config.default_scope,
        "suggested_month": ranking.suggested_target_month(session).isoformat()[:7],
        "frozen": ranking.frozen_months(session),
        "basis": ranking.BASIS,
    }


@router.get("/rankings", summary="Peringkat bulanan 65 kelurahan")
def get_ranking(
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("ranking:read"),
    month: str | None = Query(None, description="YYYY-MM; kosong = bulan yang disarankan"),
    method: str | None = Query(None),
    scope: str | None = Query(None),
) -> dict[str, Any]:
    config = ranking.load_config()
    target = _month(month, session)
    method = method or config.default_method
    scope = scope or config.default_scope
    saved = ranking.stored(session, target, method, scope)
    if saved is not None:
        return {"frozen": True, **ranking.stored_as_dict(saved)}
    try:
        computed = ranking.compute(session, target, method, scope)
    except ranking.RankingError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return {"frozen": False, **computed.as_dict()}


@router.post("/rankings/freeze", summary="Membekukan peringkat bulan sasaran")
def freeze(
    payload: FreezeRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("ranking:manage"),
) -> dict[str, Any]:
    target = _month(payload.month, session)
    try:
        computed = ranking.compute(
            session, target, payload.method, payload.scope, payload.data_cutoff
        )
        saved = ranking.freeze(session, computed, current.user.user_id)
    except ranking.RankingError as error:
        code = (
            status.HTTP_409_CONFLICT
            if "sudah dibekukan" in str(error)
            else status.HTTP_400_BAD_REQUEST
        )
        raise ApiError(code, str(error)) from error
    audit.record(
        session,
        action="FREEZE_RANKING",
        resource_type="ranking",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=str(saved.ranking_id),
        detail={
            "target_month": computed.target_month.isoformat()[:7],
            "method": computed.method,
            "scope": computed.scope,
            "data_cutoff": computed.data_cutoff.isoformat(),
        },
    )
    session.commit()
    session.refresh(saved)
    return {"frozen": True, **ranking.stored_as_dict(saved)}
