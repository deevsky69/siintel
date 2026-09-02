import { apiGet, apiPatch } from "./api";

/**
 * Administrasi pengguna dan peran (TASK 143).
 *
 * Bentuk data mengikuti `apps/api/.../routers/administration.py`. Yang perlu diingat saat
 * membaca berkas ini: layar administrasi sengaja **lebih sempit** daripada yang biasa
 * disebut manajemen pengguna.
 *
 * - Password tidak ada di sini sama sekali — bukan disembunyikan, melainkan memang tidak
 *   dapat ditetapkan lewat API. Jalurnya perintah di server (`pnpm user:password`,
 *   `pnpm prod:password`). Backend menolak 400 bila bidang password dikirim, dan
 *   alasannya dibawa apa adanya ke layar lewat `credential_basis`.
 * - Tidak ada pembuatan maupun penghapusan pengguna (`lifecycle_basis`).
 * - Peran hanya ditampilkan; sumbernya `config/rbac/permissions.yaml` (`source_basis`).
 *
 * Ketiga keterangan itu datang dari backend, bukan ditulis ulang di sini: kalimat yang
 * disalin ke frontend akan menjadi klaim yang melenceng pada hari kebijakannya berubah.
 */

export type Option = { value: string; label: string };

export type UserRow = {
  code: string;
  username: string;
  full_name: string | null;
  role_code: string;
  role: string;
  role_level: number;
  polsek: string | null;
  function: string | null;
  status: string;
  /**
   * Akun ada, tetapi belum dapat dipakai masuk: `password_hash` masih berisi penanda `!`.
   *
   * Yang dikirim backend hanya kesimpulan ini — hash-nya sendiri tidak pernah keluar dari
   * basis data.
   */
  credential_locked: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
};

export type UserDirectory = {
  data: UserRow[];
  editable_fields: string[];
  credential_basis: string;
  lifecycle_basis: string;
  polsek_options: string[];
  function_options: Option[];
  status_options: Option[];
};

export type RoleGrant = { permission: string; scope: string };

export type RoleRow = {
  code: string;
  role_name: string;
  level: number;
  user_count: number;
  active_user_count: number;
  permission_count: number;
  scopes: Record<string, number>;
  permissions: RoleGrant[];
  /** Memegang `commander_decision:approve` — inti rantai human-in-the-loop. */
  can_approve: boolean;
};

export type RoleCatalogue = {
  data: RoleRow[];
  editable: boolean;
  source_basis: string;
};

/** Label status akun mengikuti `config/taxonomy/mappings.yaml` domain `status_user`. */
export const USER_STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Aktif",
  INACTIVE: "Nonaktif",
};

/** Label cakupan pemberian permission (docs/03 §2). */
export const SCOPE_LABELS: Record<string, string> = {
  ALL: "Seluruh wilayah",
  OWN_JURISDICTION: "Wilayah sendiri",
  OWN_FUNCTION: "Fungsi sendiri",
};

/**
 * Keterangan singkat tiap cakupan, supaya artinya terbaca tanpa membuka matriks RBAC.
 *
 * Ini yang membuat daftar permission berhenti menjadi deretan kode: "boleh membaca
 * kejadian" dan "boleh membaca kejadian di wilayahnya sendiri" adalah dua kewenangan
 * yang berbeda jauh.
 */
export const SCOPE_HINTS: Record<string, string> = {
  ALL: "Berlaku atas seluruh data, tanpa batas wilayah maupun fungsi",
  OWN_JURISDICTION: "Hanya data pada Polsek yang ditetapkan pada akun",
  OWN_FUNCTION: "Hanya data pada fungsi yang ditetapkan pada akun",
};

/**
 * Profil pengguna yang sedang masuk, dari `/auth/me`.
 *
 * Dibaca di sini — dan bukan lewat `Profile` pada `lib/decisions.ts` — karena layar ini
 * membutuhkan `code`-nya: itulah yang dipakai menandai baris "akun Anda" dan mengunci
 * pilihan peran pada penugasan sendiri. Penguncian itu tetap hanya kenyamanan; yang
 * menolak perubahan peran sendiri adalah backend (409).
 */
export type SessionProfile = {
  code: string;
  username: string;
  full_name: string | null;
  role: string;
  permissions: string[];
};

export const getSessionProfile = () => apiGet<SessionProfile>("/auth/me");

export const getUsers = () => apiGet<UserDirectory>("/users");

export const getRoles = () => apiGet<RoleCatalogue>("/roles");

/**
 * Bidang yang dikirim saat memindahkan penugasan.
 *
 * Hanya empat, dan tidak satu pun di antaranya kredensial. Backend menolak selain ini —
 * daftar di sini hanya menjaga agar formulir tidak mengirim yang pasti ditolak.
 */
export type UserAssignment = {
  role_code: string;
  polsek: string | null;
  function: string | null;
  status: string;
};

/**
 * Memindahkan penugasan seorang pengguna.
 *
 * Empat penolakan — password, peran sendiri, pemegang persetujuan terakhir, dan atribut
 * cakupan yang kurang — seluruhnya ditegakkan backend (CLAUDE.md §21). Fungsi ini tidak
 * menirunya: menyalin aturan ke frontend hanya melahirkan salinan yang kelak berbeda.
 */
export const updateUserAssignment = (code: string, body: UserAssignment): Promise<UserRow> =>
  apiPatch<UserRow>(`/users/${encodeURIComponent(code)}`, body);

/**
 * Permission sebuah peran, dikelompokkan menurut resource.
 *
 * 40 baris `resource:action` yang berderet tidak terbaca sebagai kewenangan; yang terbaca
 * adalah "atas kejadian: baca, tulis, ekspor". Pengelompokan ini murni penyajian —
 * isinya tetap apa adanya dari backend.
 */
export function groupByResource(grants: RoleGrant[]): {
  resource: string;
  actions: { action: string; scope: string }[];
}[] {
  const grouped = new Map<string, { action: string; scope: string }[]>();

  for (const grant of grants) {
    const [resource, action] = grant.permission.split(":");
    const bucket = grouped.get(resource) ?? [];
    bucket.push({ action, scope: grant.scope });
    grouped.set(resource, bucket);
  }

  return [...grouped.entries()].map(([resource, actions]) => ({ resource, actions }));
}

/**
 * Cakupan yang berlaku bagi seorang pengguna, dalam kalimat.
 *
 * Akun ber-peran cakupan tanpa atributnya adalah keadaan rusak yang tidak terlihat dari
 * mana pun: setiap endpoint ber-cakupan menjawabnya 403, dan pengguna mengira sistemnya
 * yang bermasalah. Karena itu keadaan itu dinyatakan, bukan ditampilkan sebagai tanda
 * hubung yang tidak berarti apa-apa.
 */
export function assignmentSummary(user: UserRow): string {
  const parts = [
    user.polsek ? `Wilayah ${user.polsek}` : null,
    user.function ? `Fungsi ${user.function}` : null,
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" · ") : "Tanpa batas wilayah atau fungsi";
}

/**
 * Apakah penugasan pengguna ini kurang atribut yang dituntut perannya.
 *
 * Diperiksa terhadap `scopes` peran yang dikembalikan `/roles`, bukan terhadap daftar
 * nama peran — sama seperti backend.
 */
export function missingScopeAttributes(user: UserRow, role: RoleRow | undefined): string[] {
  if (!role) return [];

  const missing: string[] = [];
  if ((role.scopes.OWN_JURISDICTION ?? 0) > 0 && !user.polsek) missing.push("Polsek");
  if ((role.scopes.OWN_FUNCTION ?? 0) > 0 && !user.function) missing.push("Fungsi");
  return missing;
}
