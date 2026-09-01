"""Health endpoint (TASK 030).

Memeriksa database sungguhan, bukan sekadar membalas 200: health yang selalu hijau
tidak berguna saat demo bermasalah.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ... import __version__
from ..deps import get_db

router = APIRouter(tags=["sistem"])


@router.get("/health", summary="Status aplikasi dan database")
def health(session: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        database = {"status": "ok", "migration": revision}
    except SQLAlchemyError:
        database = {"status": "error", "migration": None}

    return {
        "name": "prediksi-presisi-api",
        "version": __version__,
        "status": "ok" if database["status"] == "ok" else "degraded",
        "database": database,
    }
