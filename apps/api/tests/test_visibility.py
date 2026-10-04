"""Batas tampilan kejadian (`services/visibility.py`).

Layar hanya boleh melihat kejadian sampai `DISPLAY_DATA_UNTIL`; evaluasi dan seeder harus
melihat semuanya. Yang dijaga: saringannya berlaku untuk SETIAP bentuk query — bukan hanya
`select(CrimeIncident)` — dan jalur bypass-nya memang membuka seluruh baris.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import CrimeIncident, Location
from prediksi_presisi_api.services import backtest, visibility
from prediksi_presisi_api.services import risk_engine as risk

DATABASE_URL = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")

CUTOFF = date(2098, 12, 31)


@pytest.fixture
def session() -> Iterator[Session]:
    visibility.install()
    db = create_engine(DATABASE_URL, future=True)
    connection = db.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    db.dispose()


@pytest.fixture
def cutoff(monkeypatch: pytest.MonkeyPatch) -> date:
    monkeypatch.setattr(visibility, "display_cutoff", lambda: CUTOFF)
    return CUTOFF


def _incident(session: Session, day: date) -> CrimeIncident:
    location = session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None
    row = CrimeIncident(
        code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
        incident_type="CURANMOR",
        occurred_at=datetime.combine(day, time(hour=10), tzinfo=UTC),
        incident_date=day,
        incident_time=time(hour=17),
        time_known=True,
        location_id=location.location_id,
        data_source="UJI",
    )
    session.add(row)
    session.flush()
    return row


def test_without_a_cutoff_everything_is_visible(session: Session) -> None:
    assert visibility.display_cutoff() is None
    row = _incident(session, date(2099, 6, 1))
    assert session.scalar(select(CrimeIncident).where(CrimeIncident.code == row.code)) is not None


@pytest.mark.parametrize(
    "shape",
    ["entity", "count", "column", "grouped", "joined", "subquery"],
)
def test_every_query_shape_hides_incidents_after_the_cutoff(
    session: Session, cutoff: date, shape: str
) -> None:
    """Satu bentuk query yang lolos berarti satu layar yang diam-diam memperlihatkan 2026."""
    inside = _incident(session, date(2098, 6, 1))
    beyond = _incident(session, date(2099, 6, 1))
    codes = (inside.code, beyond.code)

    base = select(CrimeIncident).where(CrimeIncident.code.in_(codes))
    seen: set[str]
    if shape == "entity":
        seen = {row.code for row in session.scalars(base).all()}
    elif shape == "count":
        assert session.scalar(select(func.count()).select_from(base.subquery())) == 1
        return
    elif shape == "column":
        seen = set(
            session.scalars(select(CrimeIncident.code).where(CrimeIncident.code.in_(codes))).all()
        )
    elif shape == "grouped":
        seen = {
            code
            for code, _total in session.execute(
                select(CrimeIncident.code, func.count())
                .where(CrimeIncident.code.in_(codes))
                .group_by(CrimeIncident.code)
            ).all()
        }
    elif shape == "joined":
        seen = set(
            session.scalars(
                select(CrimeIncident.code)
                .join(Location, Location.location_id == CrimeIncident.location_id)
                .where(CrimeIncident.code.in_(codes))
            ).all()
        )
    else:
        inner = select(CrimeIncident.code).where(CrimeIncident.code.in_(codes)).subquery()
        seen = set(session.scalars(select(inner.c.code)).all())

    assert seen == {inside.code}, f"bentuk query '{shape}' memperlihatkan kejadian sesudah batas"


def test_the_risk_engine_sees_only_what_the_screen_sees(session: Session, cutoff: date) -> None:
    before = risk.collect_evidence(session).total_incidents
    _incident(session, date(2099, 6, 1))
    assert risk.collect_evidence(session).total_incidents == before
    last = risk.collect_evidence(session).date_to
    assert last is None or last <= cutoff


def test_explicit_bypasses_see_everything(session: Session, cutoff: date) -> None:
    beyond = _incident(session, date(2099, 6, 1))
    statement = select(CrimeIncident.code).where(CrimeIncident.code == beyond.code)

    assert session.scalar(statement) is None
    assert session.scalar(visibility.all_incidents(statement)) == beyond.code

    visibility.see_everything(session)
    assert session.scalar(statement) == beyond.code


def test_the_backtest_evaluates_days_beyond_the_cutoff(session: Session, cutoff: date) -> None:
    """Evaluasi mundur justru hidup di luar batas tampilan — ia harus melihat 2026."""
    day = date(2099, 2, 2)
    _incident(session, day)
    summary = backtest.run_backtest(session, day, day, write=False)
    assert summary.hits + summary.false_negatives >= 1, (
        "kejadian di luar batas tidak terlihat evaluasi"
    )
