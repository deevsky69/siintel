"""Survey Rasa Aman — kanal publik dan moderasi.

```text
POST /public/reviews                 kirim ulasan (anonim, dibatasi laju)       —
GET  /public/reviews?kelurahan=      ulasan yang tayang + rata-rata             —
GET  /reviews?status=PENDING         antrean moderasi                            review:moderate
POST /reviews/{code}/moderate        PUBLISH / REJECT                            review:moderate
```
Batas dan alasannya ada di `models/area_review.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AreaReview, Location
from ...models.area_review import (
    MAX_COMMENT,
    STATUS_PENDING,
    STATUS_PUBLISHED,
    STATUS_REJECTED,
    STATUSES,
)
from ...services import audit, clock
from ..deps import CurrentUser, get_db, not_found, require_permission
from ..errors import ApiError
from .public_intake import _client_key, _RateLimiter

router = APIRouter(tags=["survey rasa aman"])

#: Tiga ulasan per jam per alamat: cukup untuk satu keluarga, terlalu sedikit untuk banjir.
limiter = _RateLimiter(3, 3600)
MAX_PUBLIC_ROWS = 50
MAX_QUEUE_ROWS = 200

REVIEW_BASIS = (
    "Ulasan anonim per kelurahan, nilai 1-5 dan komentar singkat. Tayang setelah dimoderasi "
    "(Administrator); rata-rata dihitung dari ulasan yang tayang saja. Ini persepsi warga, "
    "bukan angka kejadian."
)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kecamatan: str = Field(max_length=100)
    kelurahan: str = Field(max_length=100)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=MAX_COMMENT)


def _next_code(session: Session) -> str:
    latest = session.scalar(select(func.max(AreaReview.code)))
    if latest is None:
        return "ULS-0001"
    prefix, _, number = str(latest).rpartition("-")
    return f"{prefix}-{int(number) + 1:04d}"


def _public_row(review: AreaReview) -> dict[str, Any]:
    return {
        "code": review.code,
        "kelurahan": review.location.kelurahan,
        "kecamatan": review.location.kecamatan,
        "rating": review.rating,
        "comment": review.comment,
        "submitted_at": review.submitted_at,
    }


@router.post("/public/reviews", status_code=status.HTTP_201_CREATED, summary="Mengirim ulasan")
def submit_review(
    payload: ReviewRequest, request: Request, session: Session = Depends(get_db)
) -> dict[str, Any]:
    if not limiter.allow(_client_key(request)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak ulasan dari jaringan ini dalam satu jam terakhir.",
        )
    location = session.scalar(
        select(Location).where(
            Location.kecamatan == payload.kecamatan,
            func.lower(Location.kelurahan) == payload.kelurahan.strip().lower(),
        )
    )
    if location is None:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Kelurahan tidak dikenal pada kecamatan itu.")
    comment = (payload.comment or "").strip() or None
    review = AreaReview(
        code=_next_code(session),
        location_id=location.location_id,
        rating=payload.rating,
        comment=comment,
        submitted_at=clock.reference_now(),
        status=STATUS_PENDING,
    )
    session.add(review)
    session.flush()
    audit.record(
        session,
        action="SUBMIT_AREA_REVIEW",
        resource_type="area_review",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=review.code,
        detail={
            "kelurahan": location.kelurahan,
            "rating": payload.rating,
            "has_comment": comment is not None,
        },
    )
    session.commit()
    return {
        "code": review.code,
        "status": review.status,
        "message": "Terima kasih. Ulasan Anda akan tayang setelah diperiksa moderator.",
        "basis": REVIEW_BASIS,
    }


@router.get("/public/reviews", summary="Ulasan yang tayang untuk satu kelurahan")
def published_reviews(
    kelurahan: str = Query(max_length=100), session: Session = Depends(get_db)
) -> dict[str, Any]:
    base = (
        select(AreaReview)
        .join(Location, Location.location_id == AreaReview.location_id)
        .where(
            func.lower(Location.kelurahan) == kelurahan.strip().lower(),
            AreaReview.status == STATUS_PUBLISHED,
        )
    )
    rows = session.scalars(
        base.order_by(AreaReview.submitted_at.desc()).limit(MAX_PUBLIC_ROWS)
    ).all()
    stats = session.execute(
        select(func.avg(AreaReview.rating), func.count())
        .join(Location, Location.location_id == AreaReview.location_id)
        .where(
            func.lower(Location.kelurahan) == kelurahan.strip().lower(),
            AreaReview.status == STATUS_PUBLISHED,
        )
    ).one()
    return {
        "kelurahan": kelurahan,
        "average": round(float(stats[0]), 1) if stats[0] is not None else None,
        "count": int(stats[1] or 0),
        "data": [_public_row(row) for row in rows],
        "basis": REVIEW_BASIS,
    }


# ---------------------------------------------------------------------------
# Moderasi
# ---------------------------------------------------------------------------


def _moderation_row(review: AreaReview) -> dict[str, Any]:
    return {
        **_public_row(review),
        "status": review.status,
        "moderated_at": review.moderated_at,
        "moderated_by": review.moderator.username if review.moderator else None,
        "moderation_note": review.moderation_note,
    }


@router.get("/reviews", summary="Antrean moderasi Survey Rasa Aman")
def list_reviews(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("review:moderate"),
    status_filter: str = Query("PENDING", alias="status"),
    limit: int = Query(MAX_QUEUE_ROWS, ge=1, le=500),
) -> dict[str, Any]:
    wanted = status_filter.upper()
    if wanted not in STATUSES:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Status tidak dikenal.")
    rows = session.scalars(
        select(AreaReview)
        .where(AreaReview.status == wanted)
        .order_by(AreaReview.submitted_at.asc())
        .limit(limit)
    ).all()
    pending = session.scalar(
        select(func.count()).select_from(AreaReview).where(AreaReview.status == STATUS_PENDING)
    )
    return {"data": [_moderation_row(row) for row in rows], "pending_total": int(pending or 0)}


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(description="PUBLISH atau REJECT")
    note: str | None = Field(default=None, max_length=300)


@router.post("/reviews/{code}/moderate", summary="Menayangkan atau menolak satu ulasan")
def moderate_review(
    payload: ModerationRequest,
    code: str = Path(description="Kode ulasan, mis. ULS-0001"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("review:moderate"),
) -> dict[str, Any]:
    decision = payload.decision.upper()
    if decision not in ("PUBLISH", "REJECT"):
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Keputusan harus PUBLISH atau REJECT.")
    review = session.scalar(select(AreaReview).where(AreaReview.code == code))
    if review is None:
        raise not_found()
    new_status = STATUS_PUBLISHED if decision == "PUBLISH" else STATUS_REJECTED
    if review.status == new_status:
        raise ApiError(status.HTTP_409_CONFLICT, f"Ulasan ini sudah berstatus {review.status}.")
    previous = review.status
    review.status = new_status
    review.moderated_by = current.user.user_id
    review.moderated_at = datetime.now(UTC)
    review.moderation_note = (payload.note or "").strip() or None
    audit.record(
        session,
        action="MODERATE_AREA_REVIEW",
        resource_type="area_review",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=review.code,
        detail={"from": previous, "to": new_status, "has_note": review.moderation_note is not None},
    )
    session.commit()
    session.refresh(review)
    return _moderation_row(review)
