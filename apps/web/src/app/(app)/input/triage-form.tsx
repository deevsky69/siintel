"use client";

import { useActionState, useState } from "react";
import { triageReport } from "./actions";
import { EntryFeedback } from "./entry-feedback";
import { ENTRY_IDLE } from "./entry-state";
import { type Choice, FIELD, HINT, SUBMIT, type TriageReport } from "./options";

/**
 * Formulir triase laporan masyarakat — melengkapi MVP #12 yang selama ini hanya membaca.
 *
 * Laporan yang sedang dipilih disimpan sebagai state klien, bukan di URL: yang wajib
 * berada di URL adalah tab formulirnya, sementara pilihan di dalam satu formulir tidak
 * perlu dapat dibagikan sebagai tautan.
 *
 * Urutan status **tidak** dipaksakan. Alasannya ada di
 * `apps/api/.../routers/data_entry.py`: belum ada SOP triase yang menetapkan urutan wajib
 * maupun status akhir, sehingga melarang mundur atau melompat berarti mengarang aturan.
 * Yang dijamin sebagai gantinya adalah jejaknya — setiap perpindahan tercatat lengkap
 * dengan status sebelum dan sesudah. Keterangan itu dibawa apa adanya dari API supaya
 * layar tidak menyatakan aturan yang berbeda dari yang benar-benar ditegakkan.
 */
export function TriageForm({
  reports,
  statuses,
  verificationBasis,
  transitionBasis,
}: {
  reports: TriageReport[];
  statuses: Choice[];
  verificationBasis: string;
  transitionBasis: string;
}) {
  const [state, submit, pending] = useActionState(triageReport, ENTRY_IDLE);
  const [code, setCode] = useState("");

  const selected = reports.find((row) => row.code === code) ?? null;

  if (reports.length === 0) {
    // Daftar berasal dari `/citizen-reports` dan sudah disaring backend menurut cakupan
    // wilayah. Bila kosong, keadaannya dinyatakan — bukan diisi daftar karangan.
    return (
      <p className="text-xs leading-relaxed text-ink-muted">
        Tidak ada laporan masyarakat dalam cakupan akun Anda, sehingga tidak ada yang dapat ditriase
        dari layar ini.
      </p>
    );
  }

  return (
    <form action={submit}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="stat-label">Laporan Masyarakat</span>
          <select
            name="code"
            required
            value={code}
            onChange={(event) => setCode(event.target.value)}
            className={FIELD}
          >
            <option value="" disabled>
              Pilih laporan…
            </option>
            {reports.map((row) => (
              <option key={row.code} value={row.code}>
                {row.code} · {row.label} · {row.statusLabel}
              </option>
            ))}
          </select>
          <span className={HINT}>
            {selected
              ? `Status berjalan: ${selected.statusLabel}.`
              : "Laporan tanpa tautan sel grid tidak muncul bagi akun yang dibatasi wilayah."}
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Status Baru</span>
          <select name="status" required defaultValue="" className={FIELD}>
            <option value="" disabled>
              Pilih status…
            </option>
            {statuses.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <span className={HINT}>{transitionBasis}</span>
        </label>
      </div>

      <label className="mt-4 block">
        <span className="stat-label">Keterangan Triase</span>
        <textarea name="note" rows={2} maxLength={1000} className={FIELD} />
        <span className={HINT}>
          Ikut tersimpan di audit trail bersama status sebelum dan sesudah. Isi bila statusnya
          mundur atau melompat, supaya alasannya tidak hilang bersama orangnya.
        </span>
      </label>

      <p className="mt-4 rounded border border-base-800 bg-base-950/40 px-3 py-2 text-2xs leading-relaxed text-ink-muted">
        <strong className="text-ink">Verifikasi bukan sekadar label.</strong> {verificationBasis}
      </p>

      <EntryFeedback state={state} noun="Perubahan status" />

      <button type="submit" disabled={pending} className={SUBMIT}>
        {pending ? "Menyimpan…" : "Ubah Status Laporan"}
      </button>
    </form>
  );
}
