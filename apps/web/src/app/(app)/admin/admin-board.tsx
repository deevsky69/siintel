import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import {
  assignmentSummary,
  groupByResource,
  missingScopeAttributes,
  type RoleCatalogue,
  type RoleRow,
  SCOPE_HINTS,
  SCOPE_LABELS,
  USER_STATUS_LABELS,
  type UserDirectory,
  type UserRow,
} from "@/lib/administration";
import { formatWib } from "@/lib/warnings";
import { AssignmentForm } from "./assignment-form";

/**
 * Layar Administrasi — pengguna, peran, dan kewenangan (TASK 143).
 *
 * Layar ini menampilkan pemisahan kewenangan yang selama ini hanya hidup di
 * `config/rbac/permissions.yaml` dan di query backend. Tiga hal yang sengaja dinyatakan
 * terbuka, bukan disembunyikan:
 *
 * 1. **Password tidak ada di sini.** Jalurnya perintah di server, dan perintahnya
 *    disebutkan. Kolom yang lalu ditolak backend lebih buruk daripada tidak ada kolom.
 * 2. **Pengguna tidak dapat dibuat atau dihapus dari layar.** Penghapusan akan ditolak
 *    foreign key, pembuatan memerlukan penetapan password.
 * 3. **Peran tidak dapat disunting.** Sumbernya berkas konfigurasi; menyuntingnya lewat
 *    API akan membuat berkas itu berhenti menjadi sumber kebenaran.
 *
 * Ketiga alasan itu dibawa apa adanya dari backend (`credential_basis`, `lifecycle_basis`,
 * `source_basis`) — bukan ditulis ulang di layar, supaya tidak melenceng pada hari
 * kebijakannya berubah.
 */

function statusBadge(status: string): string {
  return status === "ACTIVE" ? "bg-risk-low/15 text-risk-low" : "bg-base-800 text-ink-muted";
}

function href(code: string): string {
  return `/admin?dipilih=${encodeURIComponent(code)}`;
}

function Row({
  user,
  role,
  selected,
  isSelf,
}: {
  user: UserRow;
  role: RoleRow | undefined;
  selected: boolean;
  isSelf: boolean;
}) {
  const missing = missingScopeAttributes(user, role);

  return (
    <li>
      <Link
        href={href(user.code)}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-950/40 hover:border-base-600"
        }`}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex-1 font-heading text-sm font-semibold text-ink">
            {user.full_name ?? user.username}
            {isSelf ? (
              <span className="ml-2 font-sans text-2xs font-normal uppercase tracking-wider text-accent">
                akun Anda
              </span>
            ) : null}
          </span>
          <span className={`badge shrink-0 ${statusBadge(user.status)}`}>
            {USER_STATUS_LABELS[user.status] ?? user.status}
          </span>
          <span
            className={`badge shrink-0 ${
              user.credential_locked
                ? "bg-risk-critical/15 text-risk-critical"
                : "bg-base-800 text-ink-muted"
            }`}
          >
            {user.credential_locked ? "Kredensial terkunci" : "Kredensial aktif"}
          </span>
        </div>
        <p className="mt-1 font-mono text-2xs uppercase tracking-wider text-ink-muted">
          {user.code} · {user.username}
        </p>
        <p className="mt-1 text-xs text-ink-muted">
          {user.role} · {assignmentSummary(user)}
        </p>
        {missing.length > 0 ? (
          <p className="mt-1 text-xs text-risk-critical">
            Penugasan tidak lengkap: peran {user.role} membutuhkan {missing.join(" dan ")}.
          </p>
        ) : null}
      </Link>
    </li>
  );
}

function Detail({
  user,
  role,
  directory,
  roles,
  canManage,
  isSelf,
}: {
  user: UserRow;
  role: RoleRow | undefined;
  directory: UserDirectory;
  roles: RoleRow[];
  canManage: boolean;
  isSelf: boolean;
}) {
  const missing = missingScopeAttributes(user, role);

  return (
    <>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt className="stat-label">Kode / Username</dt>
          <dd className="mt-0.5 font-mono text-xs text-ink">
            {user.code} · {user.username}
          </dd>
        </div>
        <div>
          <dt className="stat-label">Nama</dt>
          <dd className="mt-0.5 text-ink">{user.full_name ?? "Tidak tercatat"}</dd>
        </div>
        <div>
          <dt className="stat-label">Peran</dt>
          <dd className="mt-0.5 text-ink">
            {user.role}
            {role ? (
              <span className="text-ink-muted"> · {role.permission_count} kewenangan</span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="stat-label">Cakupan</dt>
          <dd className="mt-0.5 text-ink">{assignmentSummary(user)}</dd>
        </div>
        <div>
          <dt className="stat-label">Status Akun</dt>
          <dd className="mt-0.5 text-ink">{USER_STATUS_LABELS[user.status] ?? user.status}</dd>
        </div>
        <div>
          <dt className="stat-label">Masuk Terakhir</dt>
          <dd className="mt-0.5 text-ink">{formatWib(user.last_login_at)}</dd>
        </div>
      </dl>

      {missing.length > 0 ? (
        <p className="mt-4 rounded border border-risk-critical/40 bg-risk-critical/5 px-3 py-2 text-xs leading-relaxed text-risk-critical">
          Peran {user.role} dibatasi cakupan, tetapi akun ini belum memiliki {missing.join(" dan ")}
          . Selama begitu, setiap endpoint ber-cakupan menjawabnya 403 dan akunnya akan tampak
          seperti sistem yang rusak.
        </p>
      ) : null}

      {user.credential_locked ? (
        <p className="mt-4 rounded border border-risk-moderate/40 bg-risk-moderate/5 px-3 py-2 text-xs leading-relaxed text-risk-moderate">
          Akun ini belum memiliki kredensial: ada di basis data, tetapi tidak dapat dipakai masuk.
          Penetapannya hanya lewat perintah di server.
        </p>
      ) : user.must_change_password ? (
        <p className="mt-4 text-xs text-ink-muted">
          Akun ditandai wajib mengganti password pada kesempatan berikutnya.
        </p>
      ) : null}

      {canManage ? (
        <AssignmentForm
          user={user}
          roles={roles}
          polsekOptions={directory.polsek_options}
          functionOptions={directory.function_options}
          statusOptions={directory.status_options}
          isSelf={isSelf}
          credentialBasis={directory.credential_basis}
        />
      ) : (
        <p className="mt-4 border-t border-base-800 pt-4 text-xs leading-relaxed text-ink-muted">
          Akun Anda dapat membaca daftar ini tetapi tidak memegang <code>user:manage</code>,
          sehingga penugasan tidak dapat diubah dari sini. Pemeriksaannya ada di backend, bukan pada
          tampilan tombol.
        </p>
      )}
    </>
  );
}

function RoleCard({ role }: { role: RoleRow }) {
  const scopes = Object.entries(role.scopes).sort(([a], [b]) => a.localeCompare(b));

  return (
    <li className="rounded border border-base-800 bg-base-950/40 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex-1 font-heading text-sm font-semibold text-ink">{role.role_name}</span>
        {role.can_approve ? (
          <span className="badge shrink-0 bg-accent/15 text-accent">Menyetujui rekomendasi</span>
        ) : null}
        <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
          Level {role.level} · {role.code}
        </span>
      </div>

      <p className="mt-1 text-xs text-ink-muted">
        {role.permission_count} kewenangan · {role.active_user_count} pemegang aktif
        {role.user_count !== role.active_user_count ? ` (dari ${role.user_count} akun)` : ""}
      </p>

      {role.user_count === 0 ? (
        <p className="mt-1 text-xs text-risk-moderate">
          Tidak dipegang siapa pun — kewenangan ini tidak dapat dipakai selama peran kosong.
        </p>
      ) : null}

      <ul className="mt-2 flex flex-wrap gap-1.5">
        {scopes.map(([scope, count]) => (
          <li
            key={scope}
            title={SCOPE_HINTS[scope] ?? scope}
            className="rounded bg-base-800 px-2 py-0.5 text-2xs text-ink-muted"
          >
            {SCOPE_LABELS[scope] ?? scope}: {count}
          </li>
        ))}
      </ul>

      <details className="mt-2">
        <summary className="cursor-pointer font-heading text-xs font-semibold uppercase tracking-wider text-ink-muted hover:text-accent">
          Rincian kewenangan
        </summary>
        <ul className="mt-2 space-y-1">
          {groupByResource(role.permissions).map((group) => (
            <li key={group.resource} className="flex gap-2 text-xs">
              <span className="w-36 shrink-0 font-mono text-ink-muted">{group.resource}</span>
              <span className="text-ink">
                {group.actions
                  .map(
                    (item) =>
                      `${item.action}${
                        item.scope === "ALL" ? "" : ` (${SCOPE_LABELS[item.scope] ?? item.scope})`
                      }`,
                  )
                  .join(", ")}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}

export function AdminBoard({
  directory,
  catalogue,
  selected,
  canManage,
  currentUserCode,
}: {
  directory: UserDirectory;
  catalogue: RoleCatalogue;
  selected: UserRow | null;
  /** Menyembunyikan formulir hanyalah kenyamanan; backend tetap yang menolak. */
  canManage: boolean;
  /** Kode pengguna yang sedang masuk — dipakai menandai larangan mengubah peran sendiri. */
  currentUserCode: string;
}) {
  const roles = catalogue.data;
  const byCode = new Map(roles.map((role) => [role.code, role]));

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Panel title="Pengguna" className="xl:col-span-2">
        {directory.data.length === 0 ? (
          <EmptyState label="Belum ada pengguna dalam cakupan akun Anda." />
        ) : (
          <ul className="space-y-2">
            {directory.data.map((user) => (
              <Row
                key={user.code}
                user={user}
                role={byCode.get(user.role_code)}
                selected={selected?.code === user.code}
                isSelf={user.code === currentUserCode}
              />
            ))}
          </ul>
        )}

        <div className="mt-4 space-y-2 border-t border-base-800 pt-4 text-xs leading-relaxed text-ink-muted">
          {/* Pernyataan ini berdiri di layar, bukan hanya di dalam formulir: yang perlu tahu
              bahwa password ditetapkan lewat perintah di server adalah siapa pun yang membuka
              halaman ini, termasuk akun yang tidak berwenang mengubah penugasan. */}
          <p>{directory.credential_basis}</p>
          <p>{directory.lifecycle_basis}</p>
        </div>
      </Panel>

      <Panel title={selected ? `Penugasan · ${selected.username}` : "Penugasan"}>
        {selected ? (
          <Detail
            user={selected}
            role={byCode.get(selected.role_code)}
            directory={directory}
            roles={roles}
            canManage={canManage}
            isSelf={selected.code === currentUserCode}
          />
        ) : (
          <EmptyState label="Pilih seorang pengguna untuk melihat penugasannya." />
        )}
      </Panel>

      <Panel title="Peran & Kewenangan" className="xl:col-span-3">
        {roles.length === 0 ? (
          <EmptyState label="Katalog peran kosong — jalankan seed master data." />
        ) : (
          <ul className="grid gap-2 md:grid-cols-2">
            {roles.map((role) => (
              <RoleCard key={role.code} role={role} />
            ))}
          </ul>
        )}

        <p className="mt-4 border-t border-base-800 pt-4 text-xs leading-relaxed text-ink-muted">
          {catalogue.source_basis}
        </p>
      </Panel>
    </div>
  );
}
