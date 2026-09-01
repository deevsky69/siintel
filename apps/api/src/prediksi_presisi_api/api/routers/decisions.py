"""Keputusan komandan atas rekomendasi (TASK 130).

Titik human-in-the-loop: AI mengusulkan, **manusia memutuskan** (CLAUDE.md §13).
Tanpa berkas ini seluruh rantai `prediksi → peringatan → rekomendasi → tindakan`
akan berjalan tanpa pejabat yang bertanggung jawab — persis yang dilarang §14.

Satu endpoint menampung ketiga keputusan (`APPROVED`, `MODIFIED`, `REJECTED`) karena
keputusan adalah **entitas**, bukan tiga aksi berbeda (docs/05 §2.8). Validasi, audit,
dan aturan transisi karenanya berada di satu tempat dan tidak bisa saling menyimpang.

Yang dijaga di sini:

- rekomendasi yang sudah diputus **tidak dapat diputus ulang** diam-diam;
- `MODIFIED` wajib membawa isi baru, dan usulan asli **tidak pernah ditimpa** (U-07);
- setiap keputusan meninggalkan jejak audit beserta pejabat yang memutuskan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ...models import CommanderDecision, Location, Prediction, Recommendation
from ...services import audit
from ..deps import (
    CurrentUser,
    function_filter,
    get_db,
    jurisdiction_filter,
    not_found,
    require_permission,
)
from ..errors import ApiError

router = APIRouter(tags=["keputusan komandan"])

#: Keputusan → nama aksi audit. Menjadi satu-satunya sumber daftar keputusan yang sah,
#: sehingga menambah keputusan baru tidak bisa lupa membawa jejak auditnya.
DECISION_ACTIONS = {
    "APPROVED": "APPROVE_RECOMMENDATION",
    "MODIFIED": "MODIFY_RECOMMENDATION",
    "REJECTED": "REJECT_RECOMMENDATION",
}

MAX_HISTORY = 100


class DecisionRequest(BaseModel):
    decision: str = Field(description="APPROVED, MODIFIED, atau REJECTED")
    reason: str | None = Field(default=None, max_length=2000)
    modified_text: str | None = Field(
        default=None,
        max_length=4000,
        description="Isi rekomendasi setelah disesuaikan. Wajib bila decision = MODIFIED.",
    )


class DecisionResponse(BaseModel):
    code: str
    recommendation_code: str
    decision: str
    reason: str | None
    modified_text: str | None
    decided_by: str
    decided_at: datetime
    #: Usulan asli sistem ikut dikembalikan agar jejak "usulan AI" vs "keputusan manusia"
    #: terbaca di layar, bukan hanya tersimpan di database.
    original_recommendation: str


def _scoped_recommendations(
    query: Select[Any], polsek: str | None, function: str | None
) -> Select[Any]:
    """Membatasi rekomendasi pada cakupan pengguna — di query, bukan setelah terambil."""
    if polsek is not None:
        query = query.where(Location.polsek == polsek)
    if function is not None:
        query = query.where(Recommendation.recommended_function == function)
    return query


def _next_code(session: Session) -> str:
    """Nomor keputusan berikutnya, mengikuti format `DEC-0001` pada data awal."""
    latest = session.scalar(select(CommanderDecision.code).order_by(CommanderDecision.code.desc()))
    if latest is None:
        return "DEC-0001"
    return f"DEC-{int(latest.rsplit('-', 1)[-1]) + 1:04d}"


@router.post(
    "/recommendations/{code}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Menyetujui, memodifikasi, atau menolak rekomendasi",
)
def decide(
    code: str,
    payload: DecisionRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("commander_decision:approve"),
) -> DecisionResponse:
    decision = payload.decision.strip().upper()
    if decision not in DECISION_ACTIONS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Keputusan harus APPROVED, MODIFIED, atau REJECTED.",
        )

    modified_text = (payload.modified_text or "").strip()
    if decision == "MODIFIED" and not modified_text:
        # Aturan yang sama dijaga CHECK `ck_commander_decisions_modified_needs_text`;
        # di sini hanya agar pengguna menerima pesan yang dapat ditindaklanjuti.
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Keputusan MODIFIED wajib menyertakan isi rekomendasi yang telah disesuaikan.",
        )

    polsek = jurisdiction_filter(current, "commander_decision:approve")
    function = function_filter(current, "commander_decision:approve")
    recommendation = session.scalar(
        _scoped_recommendations(
            select(Recommendation)
            .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
            .join(Location, Location.location_id == Prediction.location_id)
            .where(Recommendation.code == code),
            polsek,
            function,
        )
    )
    if recommendation is None:
        # 404 juga untuk data di luar cakupan: 403 akan membocorkan keberadaannya.
        raise not_found()

    existing = session.scalar(
        select(CommanderDecision).where(
            CommanderDecision.recommendation_id == recommendation.recommendation_id
        )
    )
    if existing is not None:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Rekomendasi ini sudah diputus ({existing.decision}) dan tidak dapat diputus ulang.",
        )

    record = CommanderDecision(
        code=_next_code(session),
        recommendation_id=recommendation.recommendation_id,
        decision_by=current.user.user_id,
        decision=decision,
        reason=(payload.reason or "").strip() or None,
        # Usulan asli TIDAK ditimpa: `recommendation_text` tetap utuh (U-07).
        modified_text=modified_text if decision == "MODIFIED" else None,
    )
    session.add(record)

    # `recommendations.status` adalah cerminan keputusan terakhir (docs/02 §12);
    # sumber kebenarannya tetap baris keputusan di atas.
    recommendation.status = decision

    audit.record(
        session,
        action=DECISION_ACTIONS[decision],
        resource_type="recommendation",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=recommendation.code,
        detail={"decision": decision, "decision_code": record.code, "reason": record.reason},
    )
    session.commit()
    session.refresh(record)

    return DecisionResponse(
        code=record.code,
        recommendation_code=recommendation.code,
        decision=record.decision,
        reason=record.reason,
        modified_text=record.modified_text,
        decided_by=current.user.full_name or current.user.username,
        decided_at=record.decision_at,
        original_recommendation=recommendation.recommendation_text,
    )


@router.get("/commander-decisions", summary="Riwayat keputusan komandan")
def list_decisions(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("commander_decision:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "commander_decision:read")
    function = function_filter(current, "commander_decision:read")

    rows = session.execute(
        _scoped_recommendations(
            select(CommanderDecision, Recommendation, Location.kecamatan)
            .join(
                Recommendation,
                Recommendation.recommendation_id == CommanderDecision.recommendation_id,
            )
            .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
            .join(Location, Location.location_id == Prediction.location_id),
            polsek,
            function,
        )
        .order_by(CommanderDecision.decision_at.desc())
        .limit(MAX_HISTORY)
    ).all()

    return {
        "data": [
            {
                "code": record.code,
                "decision": record.decision,
                "reason": record.reason,
                "modified_text": record.modified_text,
                "decided_at": record.decision_at,
                "recommendation_code": recommendation.code,
                "recommended_function": recommendation.recommended_function,
                # Usulan asli dan hasil modifikasi berdampingan — inti bukti Taskap
                # bahwa manusia menilai, bukan sekadar meneruskan keluaran sistem.
                "original_recommendation": recommendation.recommendation_text,
                "kecamatan": kecamatan,
            }
            for record, recommendation, kecamatan in rows
        ],
        "limit": MAX_HISTORY,
    }
