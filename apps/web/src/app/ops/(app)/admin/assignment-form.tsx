"use client";

import { useActionState } from "react";
import type { Option, RoleRow, UserRow } from "@/lib/administration";
import { reassign } from "./actions";
import { ASSIGNMENT_IDLE } from "./assignment-state";

/**
 * Formulir memindahkan penugasan seorang pengguna.
 *
 * **Tidak ada kolom password di sini, dan itu disengaja.** Menyediakan kolom yang lalu
 * ditolak backend adalah bentuk kebohongan antarmuka yang paling merugikan: admin
 * mengetiknya, menekan simpan, dan mengira kredensial sudah berganti. Yang benar adalah
 * menyatakan jalurnya — perintah di server — dan tidak menawarkan jalur yang tidak ada.
 *
 * Formulir disembunyikan bagi peran tanpa `user:manage`, tetapi itu hanya kenyamanan:
 * penolakan sesungguhnya terjadi di backend (CLAUDE.md §21).
 */

const FIELD =
  "mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent disabled:opacity-50";

const HINT = "mt-1 block text-2xs leading-relaxed text-ink-muted";

export function AssignmentForm({
  user,
  roles,
  polsekOptions,
  functionOptions,
  statusOptions,
  isSelf,
  credentialBasis,
}: {
  user: UserRow;
  roles: RoleRow[];
  polsekOptions: string[];
  functionOptions: Option[];
  statusOptions: Option[];
  /** Pengguna yang sedang masuk membuka penugasannya sendiri. */
  isSelf: boolean;
  /** Alasan password tidak ada di layar ini — datang dari backend, bukan ditulis di sini. */
  credentialBasis: string;
}) {
  const [state, submit, pending] = useActionState(reassign, ASSIGNMENT_IDLE);

  return (
    <form action={submit} className="mt-4 border-t border-base-800 pt-4">
      <input type="hidden" name="code" value={user.code} />

      <label className="block">
        <span className="stat-label">Peran</span>
        {isSelf ? (
          // Kontrol yang dinonaktifkan tidak ikut terkirim, jadi nilainya dibawa input
          // tersembunyi agar permintaan tetap utuh sementara pilihannya dikunci. Penguncian
          // ini hanya kenyamanan: backend menolak 409 seandainya dipaksa lewat jalur lain.
          <input type="hidden" name="role_code" value={user.role_code} />
        ) : null}
        <select
          name="role_code"
          defaultValue={user.role_code}
          disabled={isSelf}
          required
          className={FIELD}
        >
          {roles.map((role) => (
            <option key={role.code} value={role.code}>
              {role.role_name} · {role.permission_count} kewenangan ({role.code})
            </option>
          ))}
        </select>
        {isSelf ? (
          <span className={HINT}>
            Peran akun sendiri tidak dapat diubah. Bila boleh, satu akun Administrator dapat
            mengangkat dirinya menjadi pejabat yang menyetujui rekomendasinya sendiri — dan
            pemisahan kewenangan runtuh. Mintakan perubahan ini kepada Administrator lain.
          </span>
        ) : null}
      </label>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="stat-label">Wilayah (Polsek)</span>
          <select name="polsek" defaultValue={user.polsek ?? ""} className={FIELD}>
            <option value="">Tidak ditetapkan</option>
            {polsekOptions.map((polsek) => (
              <option key={polsek} value={polsek}>
                {polsek}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="stat-label">Fungsi</span>
          <select name="function" defaultValue={user.function ?? ""} className={FIELD}>
            <option value="">Tidak ditetapkan</option>
            {functionOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <span className={HINT}>
        Peran ber-cakupan wajib punya atributnya: peran Polsek tanpa wilayah, atau peran Fungsi
        tanpa fungsi, ditolak backend. Akun seperti itu akan dijawab 403 oleh setiap endpoint
        ber-cakupan dan tampak seperti sistem yang rusak.
      </span>

      <label className="mt-3 block">
        <span className="stat-label">Status Akun</span>
        <select name="status" defaultValue={user.status} required className={FIELD}>
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span className={HINT}>
          Akun nonaktif ditolak saat masuk, bukan sekadar disembunyikan dari daftar.
        </span>
      </label>

      {state.error ? (
        <p role="alert" className="mt-3 text-xs leading-relaxed text-risk-critical">
          {state.error}
        </p>
      ) : null}

      {state.done ? (
        <p className="mt-3 text-xs text-risk-low">
          Penugasan {state.done} diperbarui dan tercatat pada audit trail beserta nilai sebelum dan
          sesudahnya.
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="mt-3 rounded bg-accent/20 px-4 py-2 font-heading text-xs font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-40"
      >
        {pending ? "Menyimpan…" : "Simpan Penugasan"}
      </button>

      <p className="mt-3 rounded border border-base-800 bg-base-850 px-3 py-2 text-2xs leading-relaxed text-ink-muted">
        <span className="font-heading font-semibold uppercase tracking-wider text-ink">
          Password tidak ada di formulir ini.
        </span>{" "}
        {credentialBasis}
      </p>
    </form>
  );
}
