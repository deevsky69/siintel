"""Test tabel publik (TASK 012): citizen_reports, public_alerts, community_feedback."""

from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint

from prediksi_presisi_api import models
from prediksi_presisi_api.db import Base

PUBLIC_TABLES = {"citizen_reports", "public_alerts", "community_feedback"}


def test_public_tables_are_registered() -> None:
    assert set(Base.metadata.tables) >= PUBLIC_TABLES


def test_citizen_report_location_is_optional() -> None:
    # Laporan masuk dengan koordinat bebas; pemetaan ke grid terjadi setelah geo-processing.
    column = Base.metadata.tables["citizen_reports"].c.location_id

    assert column.nullable is True
    foreign_keys = list(column.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].column.table.name == "locations"
    assert foreign_keys[0].ondelete == "RESTRICT"


def test_citizen_report_has_point_geometry() -> None:
    geom_type = Base.metadata.tables["citizen_reports"].c.geom.type

    assert isinstance(geom_type, Geometry)
    assert geom_type.geometry_type == "POINT"
    assert geom_type.srid == 4326


def test_citizen_report_scores_are_range_constrained() -> None:
    checks = {
        constraint.name
        for constraint in Base.metadata.tables["citizen_reports"].constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_citizen_reports_urgency_score_range" in checks
    assert "ck_citizen_reports_verification_score_range" in checks


def test_public_alert_does_not_expose_internal_location() -> None:
    # docs/02 §7: alert publik memakai area_text, bukan grid internal.
    columns = set(Base.metadata.tables["public_alerts"].c.keys())

    assert "location_id" not in columns
    assert "grid_id" not in columns
    assert "area_text" in columns


def test_public_alert_warning_link_is_optional_but_constrained() -> None:
    # Kolom dibuat pada TASK 012; FK dipasang pada TASK 013 setelah early_warnings ada.
    # Nullable karena imbauan publik dapat terbit tanpa peringatan internal.
    column = Base.metadata.tables["public_alerts"].c.warning_id

    assert column.nullable is True
    foreign_keys = list(column.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].column.table.name == "early_warnings"
    assert foreign_keys[0].ondelete == "RESTRICT"


def test_public_alert_window_order_is_constrained() -> None:
    checks = {
        constraint.name
        for constraint in Base.metadata.tables["public_alerts"].constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_public_alerts_window_order" in checks


def test_community_feedback_requires_report() -> None:
    column = models.CommunityFeedback.__table__.c.report_id

    assert column.nullable is False
    foreign_keys = list(column.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].column.table.name == "citizen_reports"
    assert foreign_keys[0].ondelete == "RESTRICT"
