"use client";

import Link from "next/link";
import { useActionState } from "react";
import type { ReportOptions, SubmitState } from "./actions";
import { submitReport } from "./actions";

/**
 * Formulir laporan masyarakat — tanpa akun, tanpa identitas.
 *
 * Tiga hal yang sengaja **tidak** ada di sini, dan ketiadaannya bukan kelalaian:
 *
 * - **Kolom nama, telepon, atau alamat pelapor.** Basis data memang tidak memiliki tempat
 *   untuk itu (`docs/02` §K, U-13). Menambahkan kolomnya di layar akan menampung data yang
 *   kemudian dibuang, dan pelapor tetap mengira datanya tersimpan.
 * - **Unggah foto atau video.** Menyimpan berkas warga menyentuh retensi dan klasifikasi
 *   data — keputusan kebijakan yang belum diambil (U-14), bukan pekerjaan yang belum sempat.
 * - **Penanda mendesak.** Tingkat urgensi ditetapkan petugas saat triase. Membiarkan
 *   pelapor mengisinya berarti membiarkan siapa pun menaikkan prioritas laporannya sendiri.
 *
 * Yang diberikan sebagai gantinya adalah **nomor tiket** — satu-satunya penanda yang
 * dipegang pelapor, dan ia tidak mengikat ke identitas siapa pun.
 */
export function ReportForm({ options }: { options: ReportOptions }) {
  const [state, action, pending] = useActionState<SubmitState, FormData>(submitReport, {
    status: "idle",
  });

  if (state.status === "sent") {
    return (
      <div className="panel">
        <div className="panel-body text-center">
          <p className="stat-label text-accent">Laporan tercatat</p>
          <p className="mt-3 text-xs text-ink-muted">Nomor tiket Anda</p>
          <p className="mt-1 font-mono text-2xl font-bold tracking-wider text-ink">
            {state.ticket}
          </p>
          <p className="mt-4 text-[11px] leading-relaxed text-ink-muted">{state.message}</p>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">{state.basis}</p>

          <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
            <Link
              href="/lapor"
              className="rounded border border-base-700 px-4 py-2 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
            >
              Kirim laporan lain
            </Link>
            <Link
              href="/"
              className="rounded border border-base-700 px-4 py-2 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
            >
              Kembali ke halaman muka
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <form action={action} className="panel">
      <div className="panel-body space-y-4">
        {state.status === "error" ? (
          <p
            role="alert"
            className="rounded border border-risk-critical/40 bg-risk-critical/10 px-3 py-2 text-xs leading-relaxed text-risk-critical"
          >
            {state.message}
          </p>
        ) : null}

        <label className="block">
          <span className="stat-label">Jenis kejadian</span>
          <select
            name="category"
            required
            defaultValue=""
            className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none"
          >
            <option value="" disabled>
              Pilih salah satu
            </option>
            {options.categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="stat-label">Kecamatan</span>
          <select
            name="kecamatan"
            required
            defaultValue=""
            className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none"
          >
            <option value="" disabled>
              Pilih kecamatan
            </option>
            {options.kecamatan.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="stat-label">Keterangan tempat (opsional)</span>
          <input
            type="text"
            name="location_text"
            maxLength={255}
            placeholder="Misalnya: gang samping pasar, dekat halte"
            className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none"
          />
        </label>

        <label className="block">
          <span className="stat-label">Waktu kejadian (opsional)</span>
          <input
            type="datetime-local"
            name="incident_time"
            className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none"
          />
          <span className="mt-1 block text-[10px] text-ink-faint">
            Dikosongkan berarti kejadiannya sedang berlangsung atau baru saja terjadi.
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Apa yang Anda lihat</span>
          <textarea
            name="description"
            required
            rows={5}
            minLength={10}
            maxLength={options.max_description}
            placeholder="Ceritakan apa yang terjadi."
            className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm leading-relaxed text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none"
          />
          <span className="mt-1 block text-[10px] leading-relaxed text-ink-faint">
            <strong>Jangan menuliskan nama, nomor telepon, atau alamat siapa pun</strong> — termasuk
            nama Anda sendiri. Sistem ini tidak menyimpan identitas, dan keterangan yang memuatnya
            justru menaruh data pribadi di tempat yang tidak dirancang untuk itu.
          </span>
        </label>

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded border border-accent/50 bg-accent/10 px-4 py-2.5 font-heading text-sm font-semibold uppercase tracking-wider text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {pending ? "Mengirim…" : "Kirim laporan"}
        </button>

        <p className="text-[10px] leading-relaxed text-ink-faint">{options.coordinate_basis}</p>
      </div>
    </form>
  );
}
