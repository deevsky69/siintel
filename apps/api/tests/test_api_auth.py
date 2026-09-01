"""Test fondasi API, autentikasi, dan otorisasi (TASK 030, 050–053).

Test yang memerlukan database memakai transaksi yang di-rollback, sehingga akun uji
tidak tertinggal di database demo.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, Role, User
from prediksi_presisi_api.security import TokenError, decode_token
from prediksi_presisi_api.security.passwords import (
    LOCKED_PASSWORD,
    hash_password,
    is_locked,
    verify_password,
)
from prediksi_presisi_api.security.tokens import create_access_token, create_refresh_token

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SECRET = "rahasia-uji-yang-panjangnya-lebih-dari-32-byte"  # noqa: S105 — nilai uji
PASSWORD = "KataSandiUji#2026"  # noqa: S105


# --------------------------------------------------------------------------------------
# Tanpa database
# --------------------------------------------------------------------------------------


def test_password_hash_is_not_reversible_and_verifies() -> None:
    stored = hash_password(PASSWORD)

    assert stored != PASSWORD
    assert stored.startswith("$argon2")
    assert verify_password(PASSWORD, stored)
    assert not verify_password("salah", stored)


def test_locked_account_can_never_authenticate() -> None:
    # Akun hasil seed terkunci sampai TASK 050 menetapkan kredensialnya.
    assert is_locked(LOCKED_PASSWORD)
    assert not verify_password(PASSWORD, LOCKED_PASSWORD)
    assert not verify_password("", LOCKED_PASSWORD)


def test_unknown_account_is_verified_without_crashing() -> None:
    # Password diverifikasi meski pengguna tidak ada, agar lamanya respons tidak
    # membedakan "akun tidak ada" dari "password salah".
    assert not verify_password(PASSWORD, None)


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    refresh, _ = create_refresh_token("USER-001", SECRET, days=7)

    with pytest.raises(TokenError, match="bukan jenis access"):
        decode_token(refresh, SECRET, "access")


def test_token_signed_with_another_secret_is_rejected() -> None:
    access, _ = create_access_token("USER-001", SECRET, minutes=15)

    with pytest.raises(TokenError):
        decode_token(access, f"{SECRET}-berbeda", "access")


def test_expired_token_is_rejected() -> None:
    access, _ = create_access_token("USER-001", SECRET, minutes=-1)

    with pytest.raises(TokenError):
        decode_token(access, SECRET, "access")


# --------------------------------------------------------------------------------------
# Dengan database
# --------------------------------------------------------------------------------------

requires_database = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()

    yield opened

    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """Client yang memakai session transaksional test."""
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def demo_user(session: Session) -> User:
    """Akun uji dengan kredensial nyata, dibuang saat transaksi di-rollback."""
    role = session.scalar(select(Role).where(Role.role_name == "Pimpinan"))
    assert role is not None

    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()
    return user


@requires_database
def test_health_reports_migration_revision(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["migration"]


@requires_database
def test_every_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["X-Request-ID"]


@requires_database
def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


@requires_database
def test_login_returns_access_token(client: TestClient, demo_user: User) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": demo_user.username, "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    # Refresh token hanya boleh berada di cookie httpOnly, tidak pernah di body.
    assert "refresh" not in response.text.lower()


@requires_database
def test_wrong_password_is_rejected_and_recorded(
    client: TestClient, session: Session, demo_user: User
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": demo_user.username, "password": "salah-sekali"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"

    denied = session.scalars(
        select(AuditLog).where(AuditLog.action == "LOGIN", AuditLog.result == "DENIED")
    ).all()
    assert denied, "percobaan masuk yang gagal harus tercatat di audit"


@requires_database
def test_seeded_accounts_cannot_log_in_until_a_password_is_set(client: TestClient) -> None:
    # Akun hasil seed sengaja terkunci; kredensial ditetapkan operator lewat CLI.
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo.pimpinan", "password": "apapun"},
    )

    assert response.status_code == 401


@requires_database
def test_protected_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@requires_database
def test_profile_lists_effective_permissions(client: TestClient, demo_user: User) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"username": demo_user.username, "password": PASSWORD},
    )
    token = login.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "Pimpinan"
    assert "commander_decision:approve" in body["permissions"]
    # Pimpinan tidak mengelola pengguna — dijaga di backend, bukan sekadar menu tersembunyi.
    assert "user:manage" not in body["permissions"]


@requires_database
def test_validation_error_uses_the_documented_contract(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": ""})

    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]
    assert body["request_id"]
