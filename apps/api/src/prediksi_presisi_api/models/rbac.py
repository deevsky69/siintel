"""Role, user, dan permission — `roles`, `users`, `permissions`, `role_permissions`.

TASK 015, docs/02 §16–§19.

Otorisasi ditegakkan di backend berdasarkan pasangan `resource:action` beserta `scope`
(CLAUDE.md §15, docs/03 §2). Frontend tidak pernah menjadi sumber kebenaran permission.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

#: Cakupan pemberian permission (docs/03 §2). Nilai teknis, bukan taksonomi bisnis.
SCOPES = ("ALL", "OWN_JURISDICTION", "OWN_FUNCTION")


class Role(TimestampMixin, Base):
    """Peran pengguna: Pimpinan, Command Center, Analyst, Fungsi, Polsek, Administrator."""

    __tablename__ = "roles"

    role_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    #: Level 1–6 sesuai docs/01 §4. Disimpan sebagai angka, bukan teks "Level 1".
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="role")
    role_permissions: Mapped[list[RolePermission]] = relationship(back_populates="role")

    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 6", name="level_range"),)


class User(TimestampMixin, Base):
    """Pengguna internal. Tidak ada pengguna publik pada PoC."""

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(150))

    #: Hash Argon2id. Password mentah tidak pernah disimpan maupun masuk dataset dummy.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="RESTRICT"),
        nullable=False,
    )

    #: Dipakai menegakkan scope OWN_JURISDICTION (docs/03 §2).
    polsek: Mapped[str | None] = mapped_column(String(100))

    #: Dipakai menegakkan scope OWN_FUNCTION (Intelkam/Reskrim/Samapta/Binmas/Lantas).
    function: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    role: Mapped[Role] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_users_role", "role_id"),
        Index("ix_users_polsek", "polsek"),
    )


class Permission(TimestampMixin, Base):
    """Satu kemampuan, dinyatakan sebagai pasangan `resource:action` (docs/03 §2)."""

    __tablename__ = "permissions"

    permission_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    role_permissions: Mapped[list[RolePermission]] = relationship(back_populates="permission")

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )


class RolePermission(Base):
    """Pemberian permission ke role beserta cakupannya."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.permission_id", ondelete="CASCADE"),
        primary_key=True,
    )

    #: ALL / OWN_JURISDICTION / OWN_FUNCTION — menggantikan simbol "L" pada draf matriks.
    scope: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ALL")

    role: Mapped[Role] = relationship(back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")

    __table_args__ = (
        CheckConstraint(
            "scope IN ('ALL', 'OWN_JURISDICTION', 'OWN_FUNCTION')",
            name="scope_allowed",
        ),
        Index("ix_role_permissions_permission", "permission_id"),
    )
