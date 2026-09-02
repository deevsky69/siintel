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

import uuid
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
    #: Perubahan yang bukan sekadar penambahan baris — misalnya cakupan yang diperbarui
    #: atau kewenangan yang dicabut. Ditampilkan supaya tidak terjadi diam-diam.
    notes: dict[str, str] = field(default_factory=dict)

    def record(self, table: str, inserted: int, skipped: int) -> None:
        self.inserted[table] = inserted
        self.skipped[table] = skipped

    def note(self, table: str, message: str) -> None:
        self.notes[table] = message

    def merge(self, other: SeedSummary) -> None:
        self.inserted.update(other.inserted)
        self.skipped.update(other.skipped)
        self.notes.update(other.notes)

    def as_lines(self) -> list[str]:
        lines = []
        for table in sorted(self.inserted):
            line = f"  {table:<20} +{self.inserted[table]:<6} (sudah ada: {self.skipped[table]})"
            if table in self.notes:
                line += f"  [{self.notes[table]}]"
            lines.append(line)
        return lines


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


def retire_unused_roles(session: Session, summary: SeedSummary) -> None:
    """Menghapus peran yang tidak lagi tercantum di `roles.csv`.

    Diperlukan sejak penggabungan peran 1 September 2026. Tanpa langkah ini, Command
    Center dan Analyst tetap hidup di basis data sebagai peran tanpa satu pun
    permission — tampak ada di daftar, tetapi tidak berarti apa-apa.

    Dipanggil **setelah** `seed_users`, bukan di dalam `seed_roles`, karena urutannya
    mengikat: pengguna harus dipindahkan ke peran barunya lebih dulu. Foreign key
    `users.role_id` bersifat RESTRICT, sehingga peran yang masih dipakai akan menolak
    dihapus dengan tegas — bukan diam-diam membuat akun kehilangan kewenangannya.
    """
    declared = {
        src.required_text(row, "role_id", "roles.csv") for row in src.read_rows("roles.csv")
    }

    session.flush()
    removed = 0
    for role in session.scalars(select(Role).where(Role.code.not_in(declared))).all():
        session.delete(role)
        removed += 1

    if removed:
        summary.note("roles", f"peran dihapus: {removed}")


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
    """Menyelaraskan `role_permissions` dengan `config/rbac/permissions.yaml`.

    **Menyelaraskan**, bukan sekadar menambah. Versi sebelumnya hanya menyisipkan
    pemberian baru dan melewati yang sudah ada, sehingga berkas konfigurasi — yang
    dinyatakan sebagai sumber kebenaran RBAC — tidak dapat mencabut apa pun maupun
    mengubah cakupan. Sebuah kewenangan yang dihapus dari berkas akan tetap hidup di
    basis data selamanya, dan tidak ada yang menyadarinya.

    Karena itu di sini ada tiga tindakan: menyisipkan yang belum ada, **memperbarui**
    cakupan yang berubah, dan **mencabut** pemberian yang tidak lagi tercantum.

    Pencabutan aman dilakukan otomatis karena `role_permissions` adalah tabel turunan
    dari berkas konfigurasi, bukan data yang dimasukkan pengguna. Yang dicabut ikut
    dilaporkan pada ringkasan agar perubahannya terlihat, bukan terjadi diam-diam.
    """
    matrix = _load_rbac(path)["roles"]

    session.flush()
    roles = {role.role_name: role for role in session.scalars(select(Role)).all()}
    permissions = {
        f"{permission.resource}:{permission.action}": permission
        for permission in session.scalars(select(Permission)).all()
    }
    current = {
        (grant.role_id, grant.permission_id): grant
        for grant in session.scalars(select(RolePermission)).all()
    }

    declared: set[tuple[uuid.UUID, uuid.UUID]] = set()
    inserted = 0
    updated = 0

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

                key = (role.role_id, permission.permission_id)
                declared.add(key)

                grant = current.get(key)
                if grant is None:
                    session.add(
                        RolePermission(
                            role_id=role.role_id,
                            permission_id=permission.permission_id,
                            scope=scope,
                        )
                    )
                    inserted += 1
                elif grant.scope != scope:
                    # Cakupan yang berubah lebih berbahaya daripada yang hilang: baris
                    # tetap ada, tetapi menegakkan batas yang berbeda dari dokumennya.
                    grant.scope = scope
                    updated += 1

    revoked = 0
    for key, grant in current.items():
        if key not in declared:
            session.delete(grant)
            revoked += 1

    summary.record("role_permissions", inserted, len(current) - revoked)
    if updated or revoked:
        summary.note(
            "role_permissions",
            f"cakupan diperbarui: {updated}, pemberian dicabut: {revoked}",
        )


def seed_users(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = _existing_codes(session, User, User.code)
    inserted = 0

    session.flush()
    roles = {role.code: role for role in session.scalars(select(Role)).all()}

    current = {user.code: user for user in session.scalars(select(User)).all()}
    reassigned = 0

    for row in src.read_rows("users.csv"):
        code = src.required_text(row, "user_id", "users.csv")
        role_code = src.required_text(row, "role_id", f"users.csv:{code}")

        if code in existing:
            # Penugasan peran berasal dari berkas seed, jadi perubahannya diikuti.
            # Password TIDAK disentuh: itu ditetapkan operator di server (TASK 050),
            # dan menimpanya di sini akan mengunci akun yang sedang dipakai.
            assigned = roles.get(role_code)
            account = current.get(code)
            if assigned is not None and account is not None and account.role_id != assigned.role_id:
                account.role_id = assigned.role_id
                reassigned += 1
            continue

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
    if reassigned:
        summary.note("users", f"penugasan peran dipindahkan: {reassigned}")


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
    # Urutan mengikat: peran lama baru boleh dihapus setelah penggunanya dipindahkan.
    retire_unused_roles(session, summary)

    # Session dibuat dengan `autoflush=False`, sehingga baris terakhir kelompok ini
    # tidak akan terlihat oleh query kelompok berikutnya bila tidak di-flush di sini.
    # Itulah yang membuat `seeding all` gagal di database kosong sementara menjalankan
    # perintah satu per satu berhasil: setiap perintah punya transaksinya sendiri.
    session.flush()

    return summary
