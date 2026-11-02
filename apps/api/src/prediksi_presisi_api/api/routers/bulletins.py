"""Buletin mingguan kelurahan (tahap 3, 2 November 2026).

```text
GET  /bulletins?week=YYYY-MM-DD&status=     daftar                      bulletin:read
POST /bulletins/generate {week?}            susun DRAFT seluruh kelurahan bulletin:manage
POST /bulletins/{id}/approve                setujui untuk dikirim       bulletin:approve
GET  /messaging/bulletins/pending           (bot) APPROVED belum terkirim + tujuannya
POST /messaging/bulletins/{id}/sent         (bot) hasil pengiriman per kanal
```
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Babinkamtibmas, Bulletin
from ...models.bulletin import STATUS_APPROVED, STATUS_DRAFT, STATUS_SENT, STATUSES
from ...services import audit, clock
from ...services import bulletin as composing
from ..deps import CurrentUser, get_db, not_found, require_permission
from ..errors import ApiError
from .messaging import require_messaging_key

router = APIRouter(tags=["buletin kelurahan"])


def _row(row: Bulletin) -> dict[str, Any]:
    return {
        "id": str(row.bulletin_id),
        "week_start": row.week_start,
        "kelurahan": row.kelurahan,
        "kecamatan": row.kecamatan,
        "polsek": row.polsek,
        "content": row.content,
        "figures": row.figures,
        "status": row.status,
        "generated_at": row.generated_at,
        "approved_at": row.approved_at,
        "sent_at": row.sent_at,
        "delivery": row.delivery,
    }


@router.get("/bulletins", summary="Daftar buletin mingguan")
def list_bulletins(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("bulletin:read"),
    week: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    status_filter: str | None = Query(None, alias="status"),
) -> dict[str, Any]:
    query = select(Bulletin)
    week_start = date.fromisoformat(week) if week else None
    if week_start:
        query = query.where(Bulletin.week_start == week_start)
    if status_filter:
        wanted = status_filter.upper()
        if wanted not in STATUSES:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Status tidak dikenal.")
        query = query.where(Bulletin.status == wanted)
    rows = session.scalars(
        query.order_by(Bulletin.week_start.desc(), Bulletin.kecamatan, Bulletin.kelurahan).limit(
            400
        )
    ).all()
    weeks = sorted(
        {row.week_start.isoformat() for row in session.scalars(select(Bulletin)).all()},
        reverse=True,
    )[:12]
    return {
        "data": [_row(row) for row in rows],
        "weeks": weeks,
        "suggested_week": composing.last_full_week().isoformat(),
        "basis": composing.BASIS,
    }


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week: str | None = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Senin minggu yang dilaporkan"
    )


@router.post("/bulletins/generate", summary="Menyusun DRAFT buletin seluruh kelurahan")
def generate_bulletins(
    payload: GenerateRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("bulletin:manage"),
) -> dict[str, Any]:
    week_start = date.fromisoformat(payload.week) if payload.week else composing.last_full_week()
    if week_start.weekday() != 0:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Minggu harus dimulai hari Senin.")
    now = datetime.now(UTC)
    created = refreshed = 0
    for kelurahan, kecamatan, polsek in composing.kelurahan_rows(session):
        content, figures = composing.compose(session, kelurahan, kecamatan, polsek, week_start)
        row = session.scalar(
            select(Bulletin).where(
                Bulletin.week_start == week_start, Bulletin.kelurahan == kelurahan
            )
        )
        if row is None:
            session.add(
                Bulletin(
                    week_start=week_start,
                    kelurahan=kelurahan,
                    kecamatan=kecamatan,
                    polsek=polsek,
                    content=content,
                    figures=figures,
                    status=STATUS_DRAFT,
                    generated_at=now,
                )
            )
            created += 1
        elif row.status == STATUS_DRAFT:
            # Draf yang belum disetujui disusun ulang; yang sudah disetujui/terkirim tidak disentuh.
            row.content, row.figures, row.generated_at = content, figures, now
            refreshed += 1
    audit.record(
        session,
        action="GENERATE_BULLETINS",
        resource_type="bulletin",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=week_start.isoformat(),
        detail={"created": created, "refreshed": refreshed},
    )
    session.commit()
    return {"week_start": week_start, "created": created, "refreshed": refreshed}


@router.post("/bulletins/{bulletin_id}/approve", summary="Menyetujui buletin untuk dikirim")
def approve_bulletin(
    bulletin_id: uuid.UUID = Path(),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("bulletin:approve"),
) -> dict[str, Any]:
    row = session.get(Bulletin, bulletin_id)
    if row is None:
        raise not_found()
    if row.status != STATUS_DRAFT:
        raise ApiError(status.HTTP_409_CONFLICT, f"Buletin ini sudah berstatus {row.status}.")
    row.status = STATUS_APPROVED
    row.approved_by = current.user.user_id
    row.approved_at = datetime.now(UTC)
    audit.record(
        session,
        action="APPROVE_BULLETIN",
        resource_type="bulletin",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=str(row.bulletin_id),
        detail={"kelurahan": row.kelurahan, "week_start": row.week_start.isoformat()},
    )
    session.commit()
    session.refresh(row)
    return _row(row)


# --- bot ---------------------------------------------------------------------------------


@router.get(
    "/messaging/bulletins/pending",
    summary="(bot) Buletin yang disetujui dan belum terkirim, beserta tujuannya",
    dependencies=[Depends(require_messaging_key)],
)
def pending_bulletins(session: Session = Depends(get_db)) -> dict[str, Any]:
    rows = session.scalars(
        select(Bulletin)
        .where(Bulletin.status == STATUS_APPROVED)
        .order_by(Bulletin.approved_at)
        .limit(100)
    ).all()
    contacts = {row.kelurahan: row for row in session.scalars(select(Babinkamtibmas)).all()}
    return {
        "data": [
            {
                **_row(row),
                "telegram_chat_id": contacts[row.kelurahan].telegram_chat_id
                if row.kelurahan in contacts
                else None,
                "whatsapp_number": contacts[row.kelurahan].whatsapp_number
                if row.kelurahan in contacts
                else None,
            }
            for row in rows
        ]
    }


class SentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delivery: dict[str, str] = Field(description='mis. {"telegram": "ok", "whatsapp": "gagal: …"}')


@router.post(
    "/messaging/bulletins/{bulletin_id}/sent",
    summary="(bot) Menandai buletin terkirim beserta hasil tiap kanal",
    dependencies=[Depends(require_messaging_key)],
)
def mark_sent(
    payload: SentRequest, bulletin_id: uuid.UUID = Path(), session: Session = Depends(get_db)
) -> dict[str, Any]:
    row = session.get(Bulletin, bulletin_id)
    if row is None:
        raise not_found()
    row.delivery = payload.delivery
    if any(value == "ok" for value in payload.delivery.values()):
        row.status = STATUS_SENT
        row.sent_at = clock.reference_now()
    audit.record(
        session,
        action="SEND_BULLETIN",
        resource_type="bulletin",
        result=audit.RESULT_SUCCESS if row.status == STATUS_SENT else audit.RESULT_FAILED,
        user_id=None,
        resource_id=str(row.bulletin_id),
        detail={"kelurahan": row.kelurahan, "delivery": payload.delivery},
    )
    session.commit()
    session.refresh(row)
    return _row(row)
