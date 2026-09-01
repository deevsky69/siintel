"""TASK 020 — Seed master data: locations, police_units, roles, permissions, users.

Sumber data:

| Tabel | Sumber |
|---|---|
| `locations`, `police_units`, `roles`, `users` | `data/sample/*.csv` |
| `permissions`, `role_permissions` | `config/rbac/permissions.yaml` |

`permissions` sengaja **tidak** diambil dari `data/sample/permissions.csv`: dataset itu hanya
memuat 12 permission tanpa `scope`, sehingga tidak lagi mencerminkan model otorisasi
pada `docs/03` §2 (43 permission + scope).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Location, Permission, PoliceUnit, Role, RolePermission, User
from . import csv_source as src
from .errors import SeedError
from .paths import RBAC_FILE
from .taxonomy import Taxonomy, load_taxonomy

#: Password akun demo sengaja DIKUNCI, bukan diisi kata sandi yang dapat ditebak.
#: Kredensial nyata baru diberikan pada TASK 050 (autentikasi). Konvensi '!' mengikuti
#: kebiasaan berkas shadow: akun ada, tetapi tidak dapat dipakai login.
LOCKED_PASSWORD = "!"  # noqa: S105 — penanda akun terkunci, bukan kata sandi

#: Atribut demo untuk menguji scope OWN_JURISDICTION / OWN_FUNCTION (docs/03 §2).
#: Dataset dummy tidak memuat kolom ini; nilainya sintetis dan hanya untuk pengembangan.
DEMO_USER_SCOPES: dict[str, dict[str, str]] = {
    "demo.polsek": {"polsek": "Polsek Tebet"},
    "demo.fungsi": {"function": "RESKRIM"},
}


@dataclass
class SeedSummary:
    """Ringkasan hasil seed per tabel."""

    inserted: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)

    def record(self, table: str, inserted: int, skipped: int) -> None:
        self.inserted[table] = inserted
        self.skipped[table] = skipped

    def as_lines(self) -> list[str]:
        return [
            f"  {table:<20} +{self.inserted[table]:<6} (sudah ada: {self.skipped[table]})"
            for table in sorted(self.inserted)
        ]


def _existing_codes(session: Session, model: Any, column: Any) -> set[str]:
    return set(session.scalars(select(column)).all())


def seed_locations(session: Session, summary: SeedSummary) -> None:
    existing = _existing_codes(session, Location, Location.code)
    inserted = 0

    for row in src.read_rows("locations.csv"):
        code = src.required_text(row, "location_id", "locations.csv")
        if code in existing:
            continue

        latitude = float(src.required_text(row, "latitude", f"locations.csv:{code}"))
        longitude = float(src.required_text(row, "longitude", f"locations.csv:{code}"))

        session.add(
            Location(
                code=code,
                grid_id=src.required_text(row, "grid_id", f"locations.csv:{code}"),
                polsek=src.required_text(row, "polsek", f"locations.csv:{code}"),
                kecamatan=src.required_text(row, "kecamatan", f"locations.csv:{code}"),
                kelurahan=src.text(row, "kelurahan"),
                grid_size_m=src.integer(row, "grid_size_m"),
                latitude=latitude,
                longitude=longitude,
                geom=f"SRID=4326;POINT({longitude} {latitude})",
                location_type=src.text(row, "location_type"),
            )
        )
        inserted += 1

    summary.record("locations", inserted, len(existing))


def seed_police_units(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = _existing_codes(session, PoliceUnit, PoliceUnit.code)
    inserted = 0

    for row in src.read_rows("police_units.csv"):
        code = src.required_text(row, "unit_id", "police_units.csv")
        if code in existing:
            continue

        session.add(
            PoliceUnit(
                code=code,
                function=taxonomy.require("function", src.text(row, "function")),
                unit_name=src.required_text(row, "unit_name", f"police_units.csv:{code}"),
                jurisdiction=src.required_text(row, "jurisdiction", f"police_units.csv:{code}"),
                status=taxonomy.require("status_unit", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("police_units", inserted, len(existing))


def seed_roles(session: Session, summary: SeedSummary) -> None:
    existing = _existing_codes(session, Role, Role.code)
    inserted = 0

    for row in src.read_rows("roles.csv"):
        code = src.required_text(row, "role_id", "roles.csv")
        if code in existing:
            continue

        raw_level = src.required_text(row, "level", f"roles.csv:{code}")
        digits = "".join(char for char in raw_level if char.isdigit())
        if not digits:
            message = f"roles.csv:{code}: level '{raw_level}' tidak memuat angka"
            raise SeedError(message)

        session.add(
            Role(
                code=code,
                role_name=src.required_text(row, "role_name", f"roles.csv:{code}"),
                level=int(digits),
            )
        )
        inserted += 1

    summary.record("roles", inserted, len(existing))


def _load_rbac(path: Path | None = None) -> dict[str, Any]:
    source = path or RBAC_FILE
    if not source.exists():
        message = f"katalog RBAC tidak ditemukan: {source}"
        raise SeedError(message)
    loaded: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))
    return loaded


def seed_permissions(session: Session, summary: SeedSummary, path: Path | None = None) -> None:
    """Memuat katalog `resource:action` dari config/rbac, bukan dari data dummy."""
    catalog = _load_rbac(path)["permissions"]
    existing = {
        (resource, action)
        for resource, action in session.execute(
            select(Permission.resource, Permission.action)
        ).all()
    }
    inserted = 0
    index = len(existing)

    for resource, actions in catalog.items():
        for action in actions:
            if (resource, action) in existing:
                continue
            index += 1
            session.add(
                Permission(
                    code=f"PERM-{index:03d}",
                    resource=resource,
                    action=action,
                    description=f"{resource}:{action}",
                )
            )
            inserted += 1

    summary.record("permissions", inserted, len(existing))


def seed_role_permissions(session: Session, summary: SeedSummary, path: Path | None = None) -> None:
    """Memberikan permission ke role beserta scope-nya (docs/03 §3, masih PROPOSED)."""
    matrix = _load_rbac(path)["roles"]

    session.flush()
    roles = {role.role_name: role for role in session.scalars(select(Role)).all()}
    permissions = {
        f"{permission.resource}:{permission.action}": permission
        for permission in session.scalars(select(Permission)).all()
    }
    existing = {
        (grant.role_id, grant.permission_id)
        for grant in session.scalars(select(RolePermission)).all()
    }
    inserted = 0

    for role_name, scopes in matrix.items():
        role = roles.get(role_name)
        if role is None:
            message = (
                f"config/rbac: role '{role_name}' tidak ada di data dummy roles.csv. "
                f"Role yang tersedia: {sorted(roles)}"
            )
            raise SeedError(message)

        for scope, entries in scopes.items():
            for entry in entries:
                permission = permissions.get(entry)
                if permission is None:
                    message = f"config/rbac: permission '{entry}' tidak ada di katalog"
                    raise SeedError(message)

                if (role.role_id, permission.permission_id) in existing:
                    continue

                session.add(
                    RolePermission(
                        role_id=role.role_id,
                        permission_id=permission.permission_id,
                        scope=scope,
                    )
                )
                existing.add((role.role_id, permission.permission_id))
                inserted += 1

    summary.record("role_permissions", inserted, 0)


def seed_users(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = _existing_codes(session, User, User.code)
    inserted = 0

    session.flush()
    roles = {role.code: role for role in session.scalars(select(Role)).all()}

    for row in src.read_rows("users.csv"):
        code = src.required_text(row, "user_id", "users.csv")
        if code in existing:
            continue

        role_code = src.required_text(row, "role_id", f"users.csv:{code}")
        role = roles.get(role_code)
        if role is None:
            message = f"users.csv:{code}: role '{role_code}' tidak ditemukan"
            raise SeedError(message)

        username = src.required_text(row, "username", f"users.csv:{code}")
        scope_attributes = DEMO_USER_SCOPES.get(username, {})

        session.add(
            User(
                code=code,
                username=username,
                full_name=src.text(row, "full_name"),
                password_hash=LOCKED_PASSWORD,
                role_id=role.role_id,
                polsek=scope_attributes.get("polsek"),
                function=scope_attributes.get("function"),
                status=taxonomy.require("status_user", src.text(row, "status")),
                must_change_password=True,
            )
        )
        inserted += 1

    summary.record("users", inserted, len(existing))


def seed_master_data(session: Session, taxonomy: Taxonomy | None = None) -> SeedSummary:
    """Menjalankan seluruh seed master data TASK 020 dalam satu transaksi pemanggil."""
    resolved = taxonomy or load_taxonomy()
    summary = SeedSummary()

    seed_locations(session, summary)
    seed_police_units(session, resolved, summary)
    seed_roles(session, summary)
    seed_permissions(session, summary)
    seed_role_permissions(session, summary)
    seed_users(session, resolved, summary)

    return summary
