"""Produk bulanan (Modul 4 mekanisme), dua tahap sejak 10 November 2026:
Analis menyusun & memeriksa (peringkat dibekukan otomatis) → Pimpinan menetapkan → pelaksanaan.

Endpoint `/kbo` dan `/kasat` (6–10 November 2026) dihapus bersama tahapnya — catatan 177."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ...services import audit
from ...services import monthly_product as products
from ...services import monthly_ranking as ranking
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError

router = APIRouter(tags=["produk bulanan"])


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    month: str = Field(pattern=r"^\d{4}-\d{2}$")


class ItemDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kelurahan: str
    status: str = "ACCEPTED"
    text: str | None = Field(default=None, max_length=2000)
    reason: str | None = Field(default=None, max_length=2000)


class AnalystRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: list[ItemDecision] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=2000)


class Selection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kelurahan: str
    action: str | None = Field(default=None, max_length=2000)


class DecideRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    selected: list[Selection]
    reason: str | None = Field(default=None, max_length=2000)


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    unit: str | None = Field(default=None, max_length=100)
    acted_at: datetime
    place: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=2000)
    result: str | None = Field(default=None, max_length=2000)


def _month(text: str) -> Any:
    try:
        return ranking.parse_month(text)
    except ranking.RankingError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, str(error)) from error


def _load(session: Session, month: str) -> Any:
    try:
        return products.load(session, _month(month))
    except products.ProductError as error:
        raise ApiError(error.status, str(error)) from error


def _audit(
    session: Session, action: str, current: CurrentUser, product: Any, detail: dict[str, Any]
) -> None:
    audit.record(
        session,
        action=action,
        resource_type="monthly_product",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=str(product.product_id),
        detail={"target_month": product.target_month.isoformat()[:7], **detail},
    )


def _run(session: Session, fn: Any) -> Any:
    # Tanpa rollback di sini: session per permintaan ditutup tanpa commit bila galat, dan
    # rollback eksplisit akan menghapus pula baris yang dibuat test pada session bersama.
    try:
        return fn()
    except products.ProductError as error:
        raise ApiError(error.status, str(error)) from error


@router.get("/monthly-products", summary="Daftar produk bulanan")
def list_products(
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("monthly_product:read"),
) -> dict[str, Any]:
    return {
        "data": products.months(session),
        "suggested_month": ranking.suggested_target_month(session).isoformat()[:7],
        "basis": products.BASIS,
    }


@router.post(
    "/monthly-products", status_code=status.HTTP_201_CREATED, summary="Menyusun draf produk bulanan"
)
def create_draft(
    payload: DraftRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("monthly_product:draft"),
) -> dict[str, Any]:
    product = _run(
        session, lambda: products.draft(session, _month(payload.month), current.user.user_id)
    )
    frozen_now = bool(product.facts.get("ranking_frozen_by_draft"))
    if frozen_now:
        # Pembekuan ikut tercatat tersendiri supaya jejaknya sama dengan pembekuan manual.
        audit.record(
            session,
            action="FREEZE_RANKING",
            resource_type="ranking",
            result=audit.RESULT_SUCCESS,
            user_id=current.user.user_id,
            resource_id=str(product.ranking_id),
            detail={"target_month": product.target_month.isoformat()[:7], "by": "draft"},
        )
    _audit(
        session,
        "DRAFT_MONTHLY_PRODUCT",
        current,
        product,
        {"items": len(product.items), "ranking_frozen_by_draft": frozen_now},
    )
    session.commit()
    return products.as_dict(products.load(session, product.target_month))


@router.get("/monthly-products/{month}", summary="Satu produk bulanan")
def get_product(
    month: str,
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("monthly_product:read"),
) -> dict[str, Any]:
    return products.as_dict(_load(session, month))


@router.post("/monthly-products/{month}/analyst", summary="Pemeriksaan analis, kirim ke Pimpinan")
def analyst(
    month: str,
    payload: AnalystRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("monthly_product:draft"),
) -> dict[str, Any]:
    product = _load(session, month)
    decisions = [item.model_dump() for item in payload.items]
    _run(
        session,
        lambda: products.analyst_review(
            session, product, decisions, payload.note, current.user.user_id
        ),
    )
    _audit(
        session,
        "REVIEW_MONTHLY_PRODUCT",
        current,
        product,
        {"stage": "ANALYST", "items": len(decisions)},
    )
    session.commit()
    return products.as_dict(_load(session, month))


@router.post("/monthly-products/{month}/decide", summary="Penetapan Pimpinan")
def decide(
    month: str,
    payload: DecideRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("monthly_product:decide"),
) -> dict[str, Any]:
    product = _load(session, month)
    selected = [row.model_dump() for row in payload.selected]
    _run(
        session,
        lambda: products.decide(session, product, selected, payload.reason, current.user.user_id),
    )
    _audit(
        session,
        "DECIDE_MONTHLY_PRODUCT",
        current,
        product,
        {"selected": [row["kelurahan"] for row in selected]},
    )
    session.commit()
    return products.as_dict(_load(session, month))


@router.post(
    "/monthly-products/{month}/items/{kelurahan}/actions",
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat kegiatan di kelurahan prioritas",
)
def record_action(
    month: str,
    kelurahan: str,
    payload: ActionRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("monthly_product:execute"),
) -> dict[str, Any]:
    product = _load(session, month)
    row = _run(
        session,
        lambda: products.record_action(
            session, product, kelurahan, current.user, payload.model_dump()
        ),
    )
    _audit(
        session,
        "RECORD_MONTHLY_ACTION",
        current,
        product,
        {"kelurahan": kelurahan, "unit": row.unit},
    )
    session.commit()
    return {
        "kelurahan": kelurahan,
        "unit": row.unit,
        "acted_at": row.acted_at,
        "place": row.place,
        "action": row.action,
        "result": row.result,
    }
