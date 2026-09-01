"""Permission efektif seorang pengguna (TASK 051).

Sumber kebenaran adalah `role_permissions` di database — bukan daftar di kode dan
bukan tampilan frontend (CLAUDE.md §15). Setiap pemberian membawa `scope`, sehingga
hasilnya bukan sekadar "boleh/tidak", melainkan "boleh atas data yang mana".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Permission, RolePermission, User

SCOPE_ALL = "ALL"
SCOPE_OWN_JURISDICTION = "OWN_JURISDICTION"
SCOPE_OWN_FUNCTION = "OWN_FUNCTION"


@dataclass(frozen=True)
class EffectivePermissions:
    """Permission seorang pengguna beserta cakupannya."""

    user_id: uuid.UUID
    role_name: str
    polsek: str | None
    function: str | None
    #: "resource:action" -> scope
    grants: dict[str, str]

    def scope_for(self, permission: str) -> str | None:
        return self.grants.get(permission)

    def allows(self, permission: str) -> bool:
        return permission in self.grants

    @property
    def permissions(self) -> list[str]:
        return sorted(self.grants)


def load_effective_permissions(session: Session, user: User) -> EffectivePermissions:
    rows = session.execute(
        select(Permission.resource, Permission.action, RolePermission.scope)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .where(RolePermission.role_id == user.role_id)
    ).all()

    grants: dict[str, str] = {}
    for resource, action, scope in rows:
        key = f"{resource}:{action}"
        # Bila satu permission diberikan dua kali dengan cakupan berbeda,
        # cakupan yang lebih luas yang berlaku.
        if grants.get(key) == SCOPE_ALL:
            continue
        grants[key] = scope

    return EffectivePermissions(
        user_id=user.user_id,
        role_name=user.role.role_name,
        polsek=user.polsek,
        function=user.function,
        grants=grants,
    )
