"""Tindakan operasional dan hasilnya (TASK 131).

Ini lengan umpan balik rantai tertutup — bagian yang sebelumnya ada datanya tetapi tidak
punya jalan masuk sama sekali:

```
… → REKOMENDASI → KEPUTUSAN → TINDAKAN OPERASIONAL → HASIL NYATA → EVALUASI
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

Tanpa lengan ini, sistem hanya dapat mengusulkan dan memutuskan, tetapi tidak pernah
tahu apakah keputusannya dijalankan dan apa hasilnya — dan success criteria #06 Taskap
justru menuntut validasi.

Invarian yang paling penting **tidak** ditegakkan di berkas ini, melainkan oleh trigger
database sejak migration 0006: tindakan operasional hanya boleh lahir dari keputusan
berstatus `APPROVED` atau `MODIFIED`. Pemeriksaan di sini hanya menghasilkan pesan yang
dapat ditindaklanjuti; yang menjamin aturannya tetap database (CLAUDE.md §13).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import (
    CommanderDecision,
    Location,
    OperationalAction,
    PoliceUnit,
    Prediction,
    Recommendation,
)
from ...services import audit, clock
from ..deps import (
    CurrentUser,
    function_filter,
    get_db,
    jurisdiction_filter,
    not_found,
    require_permission,
)
from ..errors import ApiError
from ..pagination import PageParams, page_params, paginate

#: Zona waktu penyajian. `APP_TIMEZONE` pada konfigurasi memakai nama yang sama.
WIB = timezone(timedelta(hours=7))

router = APIRouter(tags=["operasi"])

#: Status tindakan (docs/02 §14). Dikunci di sini agar tidak menyebar ke banyak tempat.
STATUS_PLANNED = "PLANNED"
STATUS_ACTIVE = "ACTIVE"
STATUS_COMPLETED = "COMPLETED"
STATUS_CANCELLED = "CANCELLED"

#: Status akhir — tidak dapat diubah lagi.
FINAL_STATUSES = (STATUS_COMPLETED, STATUS_CANCELLED)

#: Keputusan yang boleh melahirkan tindakan. Sama dengan yang dijaga trigger database.
DECISIONS_ALLOWING_ACTION = ("APPROVED", "MODIFIED")


class ActionRequest(BaseModel):
    decision_code: str = Field(description="Kode keputusan komandan yang menjadi dasar")
    unit_code: str = Field(description="Satuan yang ditugaskan")
    start_at: datetime | None = Field(
        default=None, description="Mulai penugasan. Kosong berarti waktu acuan sistem."
    )
    notes: str | None = Field(default=None, max_length=2000)


class ResultRequest(BaseModel):
    status: str = Field(description="COMPLETED atau CANCELLED")
    result: str = Field(min_length=1, max_length=4000, description="Hasil nyata di lapangan")
    end_at: datetime | None = Field(
        default=None,
        description=(
            "Waktu penugasan berakhir. Kosong berarti waktu acuan sistem — dan bila itu "
            "tidak lebih akhir daripada waktu mulai, permintaan ditolak agar durasi "
            "penugasan tidak dikarang."
        ),
    )


def _wib(moment: datetime) -> datetime:
    """Waktu dalam WIB untuk pesan yang dibaca petugas.

    Seluruh antarmuka berbahasa WIB. Pesan kesalahan yang menyebut UTC membuat petugas
    yang baru saja mengetik pukul 10.00 membaca "03.00" dan mengira sistemnya keliru —
    kesalahan yang seharusnya menuntun malah membingungkan.

    Penyimpanan tetap UTC (`timestamptz`); yang berpindah hanya penyajiannya.
    """
    return moment.astimezone(WIB)


def _scoped(query: Select[Any], polsek: str | None, function: str | None) -> Select[Any]:
    """Menyaring di query, bukan setelah data terambil.

    Wilayah diambil dari lokasi penugasan; fungsi dari satuan yang ditugaskan —
    `police_units.function`, satu-satunya jalur fungsi yang benar-benar ada pada
    model data (lihat `test_rbac_scope_enforceable`).
    """
    if polsek is not None:
        query = query.where(Location.polsek == polsek)
    if function is not None:
        query = query.where(PoliceUnit.function == function)
    return query


def _base_query() -> Select[Any]:
    return (
        select(OperationalAction, CommanderDecision, Recommendation, PoliceUnit, Location)
        .join(
            CommanderDecision,
            CommanderDecision.decision_id == OperationalAction.decision_id,
        )
        .join(
            Recommendation,
            Recommendation.recommendation_id == CommanderDecision.recommendation_id,
        )
        .join(PoliceUnit, PoliceUnit.unit_id == OperationalAction.unit_id)
        .join(Location, Location.location_id == OperationalAction.location_id)
    )


def _row(
    action: Any, decision: Any, recommendation: Any, unit: Any, location: Any
) -> dict[str, Any]:
    return {
        "code": action.code,
        "status": action.status,
        "start_at": action.start_at,
        "end_at": action.end_at,
        "result": action.result,
        "unit_code": unit.code,
        "unit_name": unit.unit_name,
        "unit_function": unit.function,
        "kecamatan": location.kecamatan,
        "kelurahan": location.kelurahan,
        "polsek": location.polsek,
        "decision_code": decision.code,
        "decision": decision.decision,
        "decision_at": decision.decision_at,
        "recommendation_code": recommendation.code,
        "recommended_function": recommendation.recommended_function,
        # Usulan asli dan hasil modifikasi dibawa bersama, sehingga layar operasi dapat
        # menunjukkan apa yang sebenarnya diperintahkan — bukan usulan mentah sistem.
        "original_recommendation": recommendation.recommendation_text,
        "modified_text": decision.modified_text,
    }


@router.get("/operations", summary="Daftar tindakan operasional")
def list_operations(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("operation:read"),
    status_filter: str | None = Query(None, alias="status"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "operation:read")
    function = function_filter(current, "operation:read")

    query = _scoped(_base_query(), polsek, function).order_by(OperationalAction.start_at.desc())
    if status_filter:
        query = query.where(OperationalAction.status == status_filter.upper())

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return paginate([_row(*row) for row in rows], total, params)


@router.get(
    "/operations/pending-decisions",
    summary="Keputusan yang disetujui tetapi belum ditindaklanjuti",
)
def pending_decisions(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("operation:read"),
) -> dict[str, Any]:
    """Keputusan `APPROVED`/`MODIFIED` yang belum punya tindakan.

    Inilah antrean kerja lapangan. Menampilkannya terpisah membuat terlihat bila
    sebuah keputusan sudah diambil tetapi tidak pernah dijalankan — keadaan yang
    sebelumnya tidak dapat dilihat dari mana pun.
    """
    polsek = jurisdiction_filter(current, "operation:read")

    query = (
        select(CommanderDecision, Recommendation, Location.kecamatan, Location.polsek)
        .join(
            Recommendation,
            Recommendation.recommendation_id == CommanderDecision.recommendation_id,
        )
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .outerjoin(
            OperationalAction,
            OperationalAction.decision_id == CommanderDecision.decision_id,
        )
        .where(CommanderDecision.decision.in_(DECISIONS_ALLOWING_ACTION))
        .where(OperationalAction.action_id.is_(None))
        .order_by(CommanderDecision.decision_at.desc())
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    rows = session.execute(query.limit(100)).all()

    return {
        "data": [
            {
                "decision_code": decision.code,
                "decision": decision.decision,
                "decision_at": decision.decision_at,
                "recommendation_code": recommendation.code,
                "recommended_function": recommendation.recommended_function,
                "original_recommendation": recommendation.recommendation_text,
                "modified_text": decision.modified_text,
                "priority": recommendation.priority,
                "kecamatan": kecamatan,
                "polsek": polsek_name,
            }
            for decision, recommendation, kecamatan, polsek_name in rows
        ]
    }


def _next_code(session: Session) -> str:
    latest = session.scalar(select(OperationalAction.code).order_by(OperationalAction.code.desc()))
    if latest is None:
        return "ACT-0001"
    return f"ACT-{int(latest.rsplit('-', 1)[-1]) + 1:04d}"


@router.post(
    "/operations",
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat penugasan lapangan dari sebuah keputusan",
)
def create_operation(
    payload: ActionRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("operation:write"),
) -> dict[str, Any]:
    decision = session.scalar(
        select(CommanderDecision).where(CommanderDecision.code == payload.decision_code)
    )
    if decision is None:
        raise not_found()

    if decision.decision not in DECISIONS_ALLOWING_ACTION:
        # Trigger database menolak hal yang sama; di sini hanya agar pesannya berguna.
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Keputusan {decision.code} berstatus {decision.decision}. Tindakan operasional "
            f"hanya boleh lahir dari keputusan yang disetujui atau dimodifikasi.",
        )

    existing = session.scalar(
        select(OperationalAction).where(OperationalAction.decision_id == decision.decision_id)
    )
    if existing is not None:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Keputusan ini sudah ditindaklanjuti oleh {existing.code}.",
        )

    unit = session.scalar(select(PoliceUnit).where(PoliceUnit.code == payload.unit_code))
    if unit is None:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Satuan tidak dikenal.")

    # Lokasi penugasan mengikuti lokasi prediksi yang mendasarinya, bukan diisi bebas:
    # tindakan harus dapat ditelusuri ke wilayah yang diprediksi.
    location_id = session.scalar(
        select(Prediction.location_id)
        .join(
            Recommendation,
            Recommendation.prediction_id == Prediction.prediction_id,
        )
        .where(Recommendation.recommendation_id == decision.recommendation_id)
    )
    if location_id is None:
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "Prediksi asal tidak memiliki lokasi.")

    action = OperationalAction(
        code=_next_code(session),
        decision_id=decision.decision_id,
        unit_id=unit.unit_id,
        location_id=location_id,
        created_by=current.user.user_id,
        # Waktu acuan aplikasi, bukan jam dinding: dataset berhenti Desember 2025 dan
        # penugasan yang tercatat sembilan bulan setelah jendelanya tidak masuk akal.
        start_at=payload.start_at or clock.reference_now(),
        status=STATUS_PLANNED,
        result=payload.notes,
    )
    session.add(action)

    audit.record(
        session,
        action="CREATE_OPERATION",
        resource_type="operation",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=action.code,
        detail={"decision_code": decision.code, "unit_code": unit.code},
    )
    session.commit()
    session.refresh(action)

    return {"code": action.code, "status": action.status, "start_at": action.start_at}


@router.post("/operations/{code}/result", summary="Mencatat hasil nyata di lapangan")
def record_result(
    code: str,
    payload: ResultRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("operation:write"),
) -> dict[str, Any]:
    new_status = payload.status.strip().upper()
    if new_status not in FINAL_STATUSES:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Status hasil harus COMPLETED atau CANCELLED.",
        )

    polsek = jurisdiction_filter(current, "operation:write")
    function = function_filter(current, "operation:write")
    row = session.execute(
        _scoped(_base_query().where(OperationalAction.code == code), polsek, function)
    ).first()
    if row is None:
        raise not_found()

    action = row[0]
    if action.status in FINAL_STATUSES:
        audit.record(
            session,
            action="RECORD_OPERATION_RESULT",
            resource_type="operation",
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            resource_id=action.code,
            detail={"reason": f"sudah berstatus akhir {action.status}"},
        )
        session.commit()
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Tindakan ini sudah berstatus {action.status} dan hasilnya tidak dapat diubah.",
        )

    end_at = payload.end_at or clock.reference_now()
    if end_at <= action.start_at:
        # Constraint `ck_operational_actions_time_order` menjaga hal yang sama di
        # database. Ditangkap lebih dulu di sini supaya pesannya dapat ditindaklanjuti.
        #
        # Keadaan ini lazim saat demo: jam acuan aplikasi beku (SDL-16), sehingga
        # penugasan yang dibuat dan diselesaikan pada sesi yang sama memiliki waktu
        # mulai dan selesai yang sama persis. Yang benar adalah **menanyakan** waktu
        # selesainya, bukan mengarang durasi agar constraint-nya lolos.
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Waktu selesai harus setelah waktu mulai "
            f"({_wib(action.start_at):%d %b %Y %H:%M} WIB). "
            f"Sertakan waktu selesai pada permintaan.",
        )

    action.status = new_status
    action.result = payload.result.strip()
    action.end_at = end_at

    audit.record(
        session,
        action="RECORD_OPERATION_RESULT",
        resource_type="operation",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=action.code,
        detail={"status": new_status},
    )
    session.commit()
    session.refresh(action)

    return {
        "code": action.code,
        "status": action.status,
        "result": action.result,
        "end_at": action.end_at,
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }
