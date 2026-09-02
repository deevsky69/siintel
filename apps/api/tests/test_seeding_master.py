"""Integration test seed master data (TASK 020) terhadap database sungguhan.

Seluruh test berjalan dalam transaksi yang di-rollback, sehingga isi database tidak berubah.
Karena seed bersifat idempoten, test ini valid baik pada database kosong (CI) maupun pada
database yang sudah ter-seed (pengembangan lokal).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import Permission, Role, RolePermission, User
from prediksi_presisi_api.security.passwords import verify_password
from prediksi_presisi_api.seeding.master import LOCKED_PASSWORD, seed_master_data

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


@pytest.fixture
def session() -> Iterator[Session]:
    """Session dalam transaksi yang selalu di-rollback."""
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    opened = factory()

    yield opened

    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


def test_master_seed_loads_expected_volumes(session: Session) -> None:
    seed_master_data(session)
    session.flush()

    counts = {
        # Kuncinya sempat bernama "locations" padahal menghitung Role — nama yang
        # keliru membuat kegagalannya sulit dibaca.
        "roles": session.scalar(select(func.count()).select_from(Role)),
        "permissions": session.scalar(select(func.count()).select_from(Permission)),
        "users": session.scalar(select(func.count()).select_from(User)),
    }

    # Empat peran sejak Command Center dan Analyst dilebur ke Administrator
    # (keputusan pemilik proyek, 1 September 2026).
    assert counts["roles"] == 4
    assert counts["permissions"] == 43  # katalog docs/03 §2
    # Enam akun tetap: dua di antaranya kini berperan Administrator. Akunnya tidak
    # dihapus karena masih dirujuk keputusan dan tindakan operasional yang tercatat.
    assert counts["users"] == 6


def test_master_seed_is_idempotent(session: Session) -> None:
    seed_master_data(session)
    session.flush()
    before = session.scalar(select(func.count()).select_from(RolePermission))

    second = seed_master_data(session)
    session.flush()
    after = session.scalar(select(func.count()).select_from(RolePermission))

    assert before == after
    assert sum(second.inserted.values()) == 0


def test_seeding_never_creates_a_usable_password(session: Session) -> None:
    """Akun yang **dibuat seed** selalu terkunci dan wajib mengganti password.

    Yang diuji perilaku seed, bukan isi tabel. Versi sebelumnya memeriksa apakah masih
    ada akun bertanda terkunci di dalam database — dan gagal begitu operator menetapkan
    password bagi seluruh akun lewat `pnpm prod:password`, padahal itu justru alur yang
    benar (TASK 050). Test yang mengunci keadaan basis data akan patah tepat ketika
    sistem mulai dipakai sungguhan.

    Karena itu tabel `users` dikosongkan lebih dulu di dalam transaksi yang dibatalkan
    setelahnya, sehingga yang diperiksa benar-benar baris yang baru dibuat seed.
    """
    session.execute(text("TRUNCATE users CASCADE"))
    seed_master_data(session)
    session.flush()

    assert LOCKED_PASSWORD == "!"  # noqa: S105 — penanda akun terkunci, bukan kata sandi
    assert not verify_password("apa pun", LOCKED_PASSWORD)

    created = session.scalars(select(User)).all()
    assert created, "seed tidak membuat satu pun akun"
    assert all(user.password_hash == LOCKED_PASSWORD for user in created)
    assert all(user.must_change_password for user in created)


def test_scope_attributes_are_present_for_limited_roles(session: Session) -> None:
    # Tanpa polsek/function, scope OWN_JURISDICTION dan OWN_FUNCTION tidak dapat diuji.
    seed_master_data(session)
    session.flush()

    polsek_user = session.scalar(select(User).where(User.username == "demo.polsek"))
    function_user = session.scalar(select(User).where(User.username == "demo.fungsi"))

    assert polsek_user is not None
    assert function_user is not None
    assert polsek_user.polsek is not None
    assert function_user.function is not None


def test_permission_grants_follow_the_documented_scopes(session: Session) -> None:
    seed_master_data(session)
    session.flush()

    scopes_by_role = {
        role_name: scope
        for role_name, scope in session.execute(
            select(Role.role_name, RolePermission.scope)
            .join(RolePermission, RolePermission.role_id == Role.role_id)
            .distinct()
        ).all()
        if scope != "ALL"
    }

    assert scopes_by_role["Polsek"] == "OWN_JURISDICTION"
    assert scopes_by_role["Fungsi"] == "OWN_FUNCTION"


def test_audit_permission_has_no_write_action(session: Session) -> None:
    """Audit bersifat append-only: tidak boleh ada permission yang mengubahnya."""
    seed_master_data(session)
    session.flush()

    audit_actions = set(
        session.scalars(select(Permission.action).where(Permission.resource == "audit")).all()
    )

    assert audit_actions == {"read"}
