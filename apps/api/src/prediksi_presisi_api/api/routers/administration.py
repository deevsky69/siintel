"""Administrasi pengguna dan peran (TASK 143).

Seluruh mekanisme yang dipakai layar ini sudah lama berjalan — `roles`,
`role_permissions`, `users`, dan audit trail ada sejak TASK 015, otorisasi sejak
TASK 052. Yang belum ada hanyalah pintu masuknya. Berkas ini menyediakannya, dan
sengaja menyediakan **lebih sedikit** daripada yang biasa disebut "manajemen pengguna":

- **Password tidak dapat ditetapkan lewat API.** Kredensial hanya ditetapkan operator
  di server (`pnpm user:password`, atau `pnpm prod:password` pada penerapan produksi —
  keduanya memanggil `prediksi_presisi_api.cli set-password`, TASK 050/SDL-06).
  Password yang dikirim ke endpoint ini **ditolak**, bukan diabaikan diam-diam: admin
  yang mengira ia baru saja mengganti password padahal tidak, adalah keadaan yang lebih
  berbahaya daripada penolakan yang terbaca.
- **Tidak ada pembuatan maupun penghapusan pengguna.** Penghapusan akan gagal pada FK
  `ondelete=RESTRICT` (pengguna dirujuk `commander_decisions`, `operational_actions`,
  `audit_logs`), dan pembuatan memerlukan penetapan password yang jalurnya sengaja
  terpisah. Keterbatasan ini dinyatakan di respons, bukan disembunyikan dari layar.
- **Peran tidak dapat disunting.** Daftar permission tiap peran berasal dari
  `config/rbac/permissions.yaml` dan diselaraskan seed. Menyuntingnya lewat API akan
  membuat berkas konfigurasi berhenti menjadi sumber kebenaran.

Empat aturan penolakan pada `PATCH /users/{code}` — password, peran sendiri, Pimpinan
terakhir, dan atribut cakupan — seluruhnya diperiksa **terhadap basis data**, bukan
terhadap daftar nama yang ditulis di kode. Peran yang boleh menyetujui dikenali dari
`commander_decision:approve` yang benar-benar dipegangnya, dan peran yang memerlukan
atribut dikenali dari `scope` pemberiannya. Dengan begitu aturannya tetap benar bila
nama peran berubah atau konfigurasi RBAC disesuaikan.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ...models import Location, Permission, Role, RolePermission, User
from ...security.passwords import is_locked
from ...seeding.taxonomy import Taxonomy, load_taxonomy
from ...services import audit
from ...services.permissions import SCOPE_OWN_FUNCTION, SCOPE_OWN_JURISDICTION
from ..deps import (
    CurrentUser,
    function_filter,
    get_db,
    jurisdiction_filter,
    not_found,
    require_permission,
)
from ..errors import ApiError

router = APIRouter(tags=["administrasi"])

#: Status akun yang membuat pengguna dapat masuk (`api/deps.py` menolak selain ini).
STATUS_ACTIVE = "ACTIVE"

#: Kewenangan yang membuat rantai human-in-the-loop dapat berjalan (CLAUDE.md §13).
APPROVAL_RESOURCE = "commander_decision"
APPROVAL_ACTION = "approve"
APPROVAL_PERMISSION = f"{APPROVAL_RESOURCE}:{APPROVAL_ACTION}"

#: Domain taksonomi pada `config/taxonomy/mappings.yaml`.
DOMAIN_USER_STATUS = "status_user"
DOMAIN_FUNCTION = "function"

#: Bidang yang boleh diubah lewat endpoint ini — penugasan, bukan identitas atau kredensial.
EDITABLE_FIELDS = ("role_code", "polsek", "function", "status")

#: Bidang yang sengaja DITANGKAP agar dapat ditolak dengan pesan yang jelas.
#: Nilainya tidak pernah dibaca, tidak pernah disimpan, dan tidak pernah masuk audit.
CREDENTIAL_FIELDS = ("password", "new_password", "password_hash", "must_change_password")

#: Mengapa password tidak ada di layar ini. Dikembalikan API supaya antarmuka tidak perlu
#: menuliskan ulang klaim yang bisa melenceng dari keadaan sebenarnya.
CREDENTIAL_BASIS = (
    "Password tidak dapat ditetapkan lewat API maupun layar. Penetapannya hanya lewat "
    "perintah di server: `pnpm user:password -- <username>` pada penerapan lokal, atau "
    "`pnpm prod:password -- <username>` pada penerapan produksi. Password dimasukkan "
    "lewat prompt tersembunyi, tidak pernah menjadi argumen perintah, dan tidak pernah "
    "melewati jalur yang sama dengan pengelolaan data (TASK 050, SDL-06). Akun berstatus "
    "kredensial 'terkunci' menyimpan penanda '!' — akunnya ada, tetapi tidak dapat "
    "dipakai masuk sampai operator menetapkan passwordnya."
)

#: Mengapa layar ini tidak membuat dan tidak menghapus pengguna.
LIFECYCLE_BASIS = (
    "Layar ini hanya memindahkan penugasan. Penghapusan pengguna tidak disediakan karena "
    "akan ditolak foreign key: pengguna dirujuk keputusan pejabat, tindakan operasional, "
    "dan audit trail yang seluruhnya bersifat permanen. Pembuatan pengguna baru tidak "
    "disediakan karena memerlukan penetapan password, dan jalur itu sengaja terpisah. "
    "Keduanya dikerjakan lewat seed dan perintah di server."
)

#: Mengapa peran tidak dapat disunting dari layar.
ROLE_SOURCE_BASIS = (
    "Daftar permission tiap peran berasal dari `config/rbac/permissions.yaml` dan "
    "diselaraskan oleh seed (`pnpm seed:master`). Berkas itulah sumber kebenarannya, "
    "bukan basis data dan bukan layar ini. Karena itu peran hanya ditampilkan: "
    "menyuntingnya lewat API akan membuat konfigurasi berhenti mencerminkan kewenangan "
    "yang sebenarnya berlaku."
)


@lru_cache(maxsize=1)
def _taxonomy() -> Taxonomy:
    """Taksonomi dibaca sekali; berkasnya konfigurasi, bukan data yang berubah tiap request."""
    return load_taxonomy()


def _options(domain: str) -> list[dict[str, str]]:
    """Nilai tersimpan → label Bahasa Indonesia, dalam urutan konfigurasi.

    Tidak ada pilihan yang dikarang di luar isi `config/taxonomy/mappings.yaml`: label
    diambil dari blok `labels` bila ada, selebihnya dari kunci sumber Bahasa Indonesia
    yang memetakan ke nilai itu (`Aktif` → `ACTIVE`).
    """
    taxonomy = _taxonomy()
    table = taxonomy.mappings.get(domain)
    if table is None:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Konfigurasi taksonomi tidak lengkap.",
        )

    explicit = taxonomy.labels.get(domain, {})
    ordered: dict[str, str] = {}
    for source, value in table.items():
        if value in ordered:
            continue
        ordered[value] = explicit.get(value, source)

    return [{"value": value, "label": label} for value, label in ordered.items()]


def _allowed(domain: str) -> list[str]:
    return [option["value"] for option in _options(domain)]


def _polsek_options(session: Session) -> list[str]:
    """Polsek yang benar-benar ada pada `locations`.

    Penugasan wilayah ke nama yang tidak ada akan menghasilkan akun yang lolos login
    tetapi tidak pernah melihat satu baris pun — rusak tanpa pesan kesalahan. Karena itu
    pilihannya diambil dari data, bukan diketik bebas.
    """
    rows = session.scalars(
        select(Location.polsek)
        .where(Location.polsek.is_not(None))
        .distinct()
        .order_by(Location.polsek)
    ).all()
    return [row for row in rows if row]


# ---------------------------------------------------------------------------
# Pembacaan
# ---------------------------------------------------------------------------


def _user_row(user: User) -> dict[str, Any]:
    """Satu baris pengguna.

    `password_hash` **tidak pernah** ikut — yang dikembalikan hanya kesimpulannya
    (terkunci atau tidak). Mengirim hash Argon2 ke antarmuka tidak menambah kegunaan
    apa pun dan menaruh materi kredensial pada jalur yang tidak memerlukannya
    (CLAUDE.md §16, §28).
    """
    return {
        "code": user.code,
        "username": user.username,
        "full_name": user.full_name,
        "role_code": user.role.code,
        "role": user.role.role_name,
        "role_level": user.role.level,
        "polsek": user.polsek,
        "function": user.function,
        "status": user.status,
        "credential_locked": is_locked(user.password_hash),
        "must_change_password": user.must_change_password,
        "last_login_at": user.last_login_at,
    }


@router.get("/users", summary="Daftar pengguna beserta penugasan dan status kredensialnya")
def list_users(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("user:read"),
) -> dict[str, Any]:
    """Pengguna internal beserta peran, cakupan, dan status kredensialnya.

    Tidak dipaginasi: jumlah pengguna PoC dihitung dengan jari, dan satu daftar utuh
    lebih sederhana daripada paginasi yang tidak pernah menyentuh halaman kedua
    (CLAUDE.md §37). Bila kelak bertambah banyak, yang benar adalah menambahkan
    paginasi — bukan memotong daftarnya diam-diam.

    Penyaringan cakupan tetap dipasang meski saat ini hanya Administrator yang memegang
    `user:read` (dengan scope `ALL`, sehingga kedua penyaring bernilai `None`). Kolom
    `users.polsek` dan `users.function` memang ada, jadi cakupannya benar-benar dapat
    ditegakkan bila kelak diberikan ke peran lain — dan yang berbahaya adalah pemberian
    ber-cakupan yang diam-diam berlaku seperti `ALL`.
    """
    polsek = jurisdiction_filter(current, "user:read")
    function = function_filter(current, "user:read")

    query = select(User).options(joinedload(User.role)).join(Role, Role.role_id == User.role_id)
    if polsek is not None:
        query = query.where(User.polsek == polsek)
    if function is not None:
        query = query.where(User.function == function)

    rows = session.scalars(query.order_by(Role.level, User.code)).all()

    return {
        "data": [_user_row(user) for user in rows],
        "editable_fields": list(EDITABLE_FIELDS),
        "credential_basis": CREDENTIAL_BASIS,
        "lifecycle_basis": LIFECYCLE_BASIS,
        # Pilihan penugasan diambil dari data dan konfigurasi, bukan diketik ulang di layar.
        "polsek_options": _polsek_options(session),
        "function_options": _options(DOMAIN_FUNCTION),
        "status_options": _options(DOMAIN_USER_STATUS),
    }


@router.get("/roles", summary="Daftar peran beserta kewenangan dan jumlah pemegangnya")
def list_roles(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("role:read"),
) -> dict[str, Any]:
    """Peran, kewenangan beserta cakupannya, dan jumlah pengguna yang memegangnya.

    Jumlah pemegang ditampilkan karena itulah yang membuat matriks kewenangan berhenti
    menjadi dokumen: peran dengan nol pemegang berarti ada endpoint yang tidak dapat
    dipakai siapa pun — keadaan yang pernah benar-benar terjadi pada `intelligence:write`
    (lihat catatan 1 September 2026 pada `config/rbac/permissions.yaml`).
    """
    del current  # otorisasi sudah ditegakkan dependency; tidak ada penyaringan lain.

    holders: dict[uuid.UUID, int] = {
        role_id: total
        for role_id, total in session.execute(
            select(User.role_id, func.count(User.user_id)).group_by(User.role_id)
        ).all()
    }
    active_holders: dict[uuid.UUID, int] = {
        role_id: total
        for role_id, total in session.execute(
            select(User.role_id, func.count(User.user_id))
            .where(User.status == STATUS_ACTIVE)
            .group_by(User.role_id)
        ).all()
    }

    grants: dict[uuid.UUID, list[dict[str, str]]] = {}
    for role_id, resource, action, scope in session.execute(
        select(RolePermission.role_id, Permission.resource, Permission.action, RolePermission.scope)
        .join(Permission, Permission.permission_id == RolePermission.permission_id)
        .order_by(Permission.resource, Permission.action)
    ).all():
        grants.setdefault(role_id, []).append(
            {"permission": f"{resource}:{action}", "scope": scope}
        )

    roles = session.scalars(select(Role).order_by(Role.level)).all()

    return {
        "data": [
            {
                "code": role.code,
                "role_name": role.role_name,
                "level": role.level,
                "user_count": holders.get(role.role_id, 0),
                "active_user_count": active_holders.get(role.role_id, 0),
                "permission_count": len(grants.get(role.role_id, [])),
                "scopes": _scope_summary(grants.get(role.role_id, [])),
                "permissions": grants.get(role.role_id, []),
                "can_approve": any(
                    item["permission"] == APPROVAL_PERMISSION
                    for item in grants.get(role.role_id, [])
                ),
            }
            for role in roles
        ],
        "editable": False,
        "source_basis": ROLE_SOURCE_BASIS,
    }


def _scope_summary(items: list[dict[str, str]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in items:
        summary[item["scope"]] = summary.get(item["scope"], 0) + 1
    return summary


# ---------------------------------------------------------------------------
# Pemindahan penugasan
# ---------------------------------------------------------------------------


class UserAssignmentRequest(BaseModel):
    """Perubahan penugasan seorang pengguna.

    `extra="ignore"` adalah pengaman privasi yang sama dengan `data_entry.py`: bidang
    yang tidak dikenal tidak disimpan, tidak dikembalikan, dan **tidak ikut masuk ke
    detail audit**. Yang berbeda di sini, bidang bernuansa kredensial justru
    dideklarasikan agar dapat **ditolak** — diabaikan diam-diam akan membuat admin
    mengira password sudah berganti padahal tidak.
    """

    model_config = ConfigDict(extra="ignore")

    role_code: str | None = Field(default=None, description="Kode peran, mis. ROLE-01")
    polsek: str | None = Field(default=None, description="Penugasan wilayah, boleh dikosongkan")
    function: str | None = Field(default=None, description="Penugasan fungsi, boleh dikosongkan")
    status: str | None = Field(default=None, description="ACTIVE atau INACTIVE")

    # Ditangkap untuk ditolak. Nilainya tidak pernah dibaca.
    password: Any = None
    new_password: Any = None
    password_hash: Any = None
    must_change_password: Any = None


def _role_grants(session: Session, role_id: uuid.UUID) -> list[tuple[str, str, str]]:
    rows = session.execute(
        select(Permission.resource, Permission.action, RolePermission.scope)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .where(RolePermission.role_id == role_id)
    ).all()
    return [(resource, action, scope) for resource, action, scope in rows]


def _role_can_approve(session: Session, role_id: uuid.UUID) -> bool:
    """Peran ini memegang `commander_decision:approve` — menurut basis data.

    Bukan menurut nama perannya: memeriksa `role_name == "Pimpinan"` akan menjadi salah
    diam-diam pada hari nama peran berubah, dan yang harus dijaga adalah kemampuannya,
    bukan namanya.
    """
    return any(
        resource == APPROVAL_RESOURCE and action == APPROVAL_ACTION
        for resource, action, _ in _role_grants(session, role_id)
    )


def _required_attributes(session: Session, role_id: uuid.UUID) -> set[str]:
    """Atribut yang wajib dimiliki akun agar peran ini dapat dipakai.

    Diturunkan dari `scope` pemberiannya, bukan dari daftar tetap: peran dengan
    pemberian `OWN_JURISDICTION` mustahil dipakai tanpa `polsek`, dan `OWN_FUNCTION`
    tanpa `function` — `api/deps.py` menolak keduanya dengan 403 pada setiap endpoint
    ber-cakupan. Akun seperti itu tampak seperti sistem yang rusak, padahal
    penugasannya yang tidak lengkap.
    """
    required: set[str] = set()
    for _, _, scope in _role_grants(session, role_id):
        if scope == SCOPE_OWN_JURISDICTION:
            required.add("polsek")
        elif scope == SCOPE_OWN_FUNCTION:
            required.add("function")
    return required


def _remaining_approvers(session: Session, *, excluding: uuid.UUID) -> int:
    """Jumlah akun aktif selain `excluding` yang masih dapat menyetujui rekomendasi."""
    return (
        session.scalar(
            select(func.count(func.distinct(User.user_id)))
            .select_from(User)
            .join(RolePermission, RolePermission.role_id == User.role_id)
            .join(Permission, Permission.permission_id == RolePermission.permission_id)
            .where(Permission.resource == APPROVAL_RESOURCE)
            .where(Permission.action == APPROVAL_ACTION)
            .where(User.status == STATUS_ACTIVE)
            .where(User.user_id != excluding)
        )
        or 0
    )


def _refuse(
    session: Session,
    *,
    user_id: uuid.UUID,
    resource_id: str,
    reason: str,
    http_status: int,
    message: str,
) -> ApiError:
    """Mencatat penolakan lalu menyiapkan kesalahannya.

    Percobaan yang ditolak ikut meninggalkan jejak — terutama percobaan menaikkan peran
    sendiri, yang justru paling perlu terlihat (CLAUDE.md §29). `reason` hanya memuat
    nama aturan yang dilanggar; tidak ada isi permintaan yang disalin ke sini.
    """
    audit.record(
        session,
        action="UPDATE_USER",
        resource_type="user",
        result=audit.RESULT_FAILED,
        user_id=user_id,
        resource_id=resource_id,
        detail={"reason": reason},
    )
    session.commit()
    return ApiError(http_status, message)


@router.patch("/users/{code}", summary="Memindahkan penugasan seorang pengguna")
def update_user(
    code: str,
    payload: UserAssignmentRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("user:manage"),
) -> dict[str, Any]:
    """Mengubah peran, wilayah, fungsi, atau status seorang pengguna.

    Empat penolakan yang ditegakkan di sini, beserta alasannya:

    1. **Password (400).** Kredensial tidak melewati jalur pengelolaan data.
    2. **Peran sendiri (409).** Bila boleh, seorang Administrator dapat mengangkat
       dirinya menjadi Pimpinan dan seluruh pemisahan kewenangan runtuh — termasuk
       larangan "yang mengusulkan bukan yang memutuskan".
    3. **Pemegang persetujuan terakhir (409).** Tanpa akun aktif yang dapat menyetujui,
       rekomendasi tidak pernah menjadi tindakan dan rantai human-in-the-loop mati.
    4. **Atribut cakupan (400).** Peran ber-cakupan tanpa atributnya menghasilkan akun
       yang ditolak setiap endpoint ber-cakupan.
    """
    changes = payload.model_fields_set

    sent_credentials = [field for field in CREDENTIAL_FIELDS if field in changes]
    if sent_credentials:
        # Ditolak, bukan diabaikan. Yang tercatat hanya NAMA bidangnya — nilainya tidak
        # pernah dibaca, tidak masuk pesan kesalahan, dan tidak masuk audit. Percobaannya
        # sendiri dicatat: upaya menetapkan kredensial lewat jalur pengelolaan data adalah
        # peristiwa yang perlu terlihat, sekalipun ia hanya salah paham (CLAUDE.md §29).
        raise _refuse(
            session,
            user_id=current.user.user_id,
            # Kode datang dari path dan belum tentu ada; dipotong sepanjang kolomnya.
            resource_id=code[:100],
            reason=f"bidang kredensial ditolak: {', '.join(sorted(sent_credentials))}",
            http_status=status.HTTP_400_BAD_REQUEST,
            message=(
                f"Bidang {', '.join(sorted(sent_credentials))} tidak diterima endpoint ini. "
                f"{CREDENTIAL_BASIS}"
            ),
        )

    requested = [field for field in EDITABLE_FIELDS if field in changes]
    if not requested:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Tidak ada perubahan yang diminta. Bidang yang dapat diubah: "
            f"{', '.join(EDITABLE_FIELDS)}.",
        )

    target = session.scalar(select(User).options(joinedload(User.role)).where(User.code == code))
    if target is None:
        raise not_found()

    before = {
        "role_code": target.role.code,
        "polsek": target.polsek,
        "function": target.function,
        "status": target.status,
    }

    # --- peran -------------------------------------------------------------
    new_role = target.role
    if "role_code" in changes:
        if payload.role_code is None:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Peran tidak boleh dikosongkan.")

        resolved = session.scalar(select(Role).where(Role.code == payload.role_code))
        if resolved is None:
            raise ApiError(
                status.HTTP_400_BAD_REQUEST,
                f"Peran '{payload.role_code}' tidak dikenal.",
            )

        if resolved.role_id != target.role_id and target.user_id == current.user.user_id:
            raise _refuse(
                session,
                user_id=current.user.user_id,
                resource_id=target.code,
                reason="pengguna mengubah perannya sendiri",
                http_status=status.HTTP_409_CONFLICT,
                message=(
                    "Peran akun sendiri tidak dapat diubah. Kewenangan yang memberikan "
                    "kewenangan tidak boleh dipakai atas diri sendiri: bila boleh, satu "
                    "akun Administrator dapat mengangkat dirinya menjadi pejabat yang "
                    "menyetujui rekomendasinya sendiri. Mintakan perubahan ini kepada "
                    "Administrator lain."
                ),
            )

        new_role = resolved

    # --- status ------------------------------------------------------------
    new_status = target.status
    if "status" in changes:
        if payload.status is None:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Status tidak boleh dikosongkan.")

        candidate = payload.status.strip().upper()
        if candidate not in _allowed(DOMAIN_USER_STATUS):
            raise ApiError(
                status.HTTP_400_BAD_REQUEST,
                f"Status '{payload.status}' tidak dikenal. "
                f"Yang sah: {', '.join(_allowed(DOMAIN_USER_STATUS))}.",
            )
        new_status = candidate

    # --- wilayah dan fungsi ------------------------------------------------
    new_polsek = target.polsek
    if "polsek" in changes:
        if payload.polsek is None or payload.polsek.strip() == "":
            new_polsek = None
        else:
            candidate = payload.polsek.strip()
            available = _polsek_options(session)
            if candidate not in available:
                raise ApiError(
                    status.HTTP_400_BAD_REQUEST,
                    f"Polsek '{candidate}' tidak ada pada data wilayah. "
                    f"Yang tersedia: {', '.join(available)}.",
                )
            new_polsek = candidate

    new_function = target.function
    if "function" in changes:
        if payload.function is None or payload.function.strip() == "":
            new_function = None
        else:
            candidate = payload.function.strip().upper()
            if candidate not in _allowed(DOMAIN_FUNCTION):
                raise ApiError(
                    status.HTTP_400_BAD_REQUEST,
                    f"Fungsi '{payload.function}' tidak dikenal. "
                    f"Yang sah: {', '.join(_allowed(DOMAIN_FUNCTION))}.",
                )
            new_function = candidate

    # --- rantai persetujuan tidak boleh putus ------------------------------
    #
    # Diperiksa terhadap keadaan HASIL, bukan terhadap satu bidang saja: memindahkan
    # peran dan menonaktifkan akun sama-sama menghilangkan kemampuan menyetujui.
    was_approver = _role_can_approve(session, target.role_id) and target.status == STATUS_ACTIVE
    still_approver = _role_can_approve(session, new_role.role_id) and new_status == STATUS_ACTIVE

    if (
        was_approver
        and not still_approver
        and _remaining_approvers(session, excluding=target.user_id) == 0
    ):
        raise _refuse(
            session,
            user_id=current.user.user_id,
            resource_id=target.code,
            reason="akan menghabiskan pemegang commander_decision:approve",
            http_status=status.HTTP_409_CONFLICT,
            message=(
                f"{target.username} adalah satu-satunya akun aktif yang masih dapat "
                f"menyetujui rekomendasi ({APPROVAL_PERMISSION}). Perubahan ini akan "
                "membuat peran itu tidak dipegang siapa pun: rekomendasi tidak akan "
                "pernah menjadi tindakan, dan rantai human-in-the-loop berhenti. "
                "Tetapkan penggantinya lebih dahulu, lalu ulangi perubahan ini."
            ),
        )

    # --- peran ber-cakupan wajib punya atributnya --------------------------
    required = _required_attributes(session, new_role.role_id)
    resulting = {"polsek": new_polsek, "function": new_function}
    missing = sorted(field for field in required if resulting[field] is None)
    if missing:
        raise _refuse(
            session,
            user_id=current.user.user_id,
            resource_id=target.code,
            reason=f"peran {new_role.code} tanpa atribut cakupan: {', '.join(missing)}",
            http_status=status.HTTP_400_BAD_REQUEST,
            message=(
                f"Peran {new_role.role_name} dibatasi cakupan, sehingga akun wajib "
                f"memiliki {', '.join(missing)}. Tanpa itu setiap endpoint ber-cakupan "
                "menolak akun ini dengan 403, dan akunnya akan tampak seperti sistem "
                "yang rusak. Sertakan atributnya pada permintaan yang sama."
            ),
        )

    after = {
        "role_code": new_role.code,
        "polsek": new_polsek,
        "function": new_function,
        "status": new_status,
    }
    if after == before:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Nilai yang dikirim sama dengan yang berlaku sekarang; tidak ada yang diubah.",
        )

    target.role_id = new_role.role_id
    target.polsek = new_polsek
    target.function = new_function
    target.status = new_status

    audit.record(
        session,
        action="UPDATE_USER",
        resource_type="user",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=target.code,
        # Hanya empat bidang penugasan yang dicatat. Tidak ada kredensial, tidak ada
        # bidang tak dikenal yang terlanjur dikirim klien (CLAUDE.md §16, §29).
        detail={"before": before, "after": after},
    )
    session.commit()
    session.refresh(target)

    return _user_row(target)
