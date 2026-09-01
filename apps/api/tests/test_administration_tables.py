"""Test tabel administrasi (TASK 015): roles, users, permissions, role_permissions, audit_logs."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from prediksi_presisi_api.db import Base
from prediksi_presisi_api.models.audit_log import AUDIT_RESULTS
from prediksi_presisi_api.models.rbac import SCOPES

ADMIN_TABLES = {"roles", "users", "permissions", "role_permissions", "audit_logs"}


def test_administration_tables_are_registered() -> None:
    assert set(Base.metadata.tables) >= ADMIN_TABLES


def test_user_can_store_credentials_and_scope_attributes() -> None:
    # Tanpa kolom ini, TASK 050 (autentikasi) dan scope OWN_JURISDICTION/OWN_FUNCTION
    # pada docs/03 §2 tidak dapat ditegakkan di backend.
    columns = Base.metadata.tables["users"].c

    assert columns.password_hash.nullable is False
    assert "polsek" in columns
    assert "function" in columns
    assert "last_login_at" in columns
    assert columns.must_change_password.nullable is False


def test_role_level_is_constrained() -> None:
    checks = {
        constraint.name
        for constraint in Base.metadata.tables["roles"].constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_roles_level_range" in checks


def test_permission_pair_is_unique() -> None:
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in Base.metadata.tables["permissions"].constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("resource", "action") in unique_columns


def test_role_permission_carries_scope() -> None:
    table = Base.metadata.tables["role_permissions"]

    assert table.c.scope.nullable is False
    assert set(table.primary_key.columns.keys()) == {"role_id", "permission_id"}

    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_role_permissions_scope_allowed" in checks


def test_role_permission_is_removed_with_its_role() -> None:
    # Mencabut role tidak boleh meninggalkan pemberian permission yang menggantung.
    for column_name in ("role_id", "permission_id"):
        foreign_keys = list(Base.metadata.tables["role_permissions"].c[column_name].foreign_keys)

        assert len(foreign_keys) == 1
        assert foreign_keys[0].ondelete == "CASCADE"


def test_audit_log_records_denied_attempts() -> None:
    # Tanpa nilai DENIED, penolakan otorisasi tidak terekam padahal itu bukti RBAC bekerja.
    assert AUDIT_RESULTS == ("SUCCESS", "DENIED", "FAILED")

    checks = {
        constraint.name
        for constraint in Base.metadata.tables["audit_logs"].constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_audit_logs_result_allowed" in checks


def test_audit_log_user_is_optional_for_system_events() -> None:
    assert Base.metadata.tables["audit_logs"].c.user_id.nullable is True


def test_audit_log_has_no_updated_at() -> None:
    # Audit bersifat append-only (CLAUDE.md §29): tidak ada jalur pembaruan baris.
    columns = set(Base.metadata.tables["audit_logs"].c.keys())

    assert "updated_at" not in columns


def test_scope_values_are_documented() -> None:
    assert SCOPES == ("ALL", "OWN_JURISDICTION", "OWN_FUNCTION")
