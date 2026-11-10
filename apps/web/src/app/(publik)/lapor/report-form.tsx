"use client";

import Link from "next/link";
import { useActionState } from "react";
import { Basis } from "@/components/basis";
import type { ReportOptions, SubmitState } from "./actions";
import { submitReport } from "./actions";
import { AreaPicker } from "./area-picker";
import { AttachFiles } from "./attach-files";

/**
 * Formulir laporan masyarakat — tanpa akun, tanpa identitas (mockup 10 November 2026:
 * tiga fieldset bernomor dalam kartu putih, kartu pilihan jenis, tombol navy).
 *
 * Dua hal yang sengaja **tidak** ada di sini, dan ketiadaannya bukan kelalaian:
 *
 * - **Kolom nama, telepon, atau alamat pelapor** (blok "4 Kontak pelapor" pada mockup).
 *   Basis data memang tidak memiliki tempat untuk itu (`docs/02` §K, U-13). Menambahkan
 *   kolomnya di layar akan menampung data yang kemudian dibuang, dan pelapor tetap mengira
 *   datanya tersimpan. Menyimpannya adalah keputusan privasi pemilik proyek, bukan teknis.
 * - **Penanda mendesak.** Tingkat urgensi ditetapkan petugas saat triase.
 *
 * Yang diberikan sebagai gantinya adalah **nomor tiket** — satu-satunya penanda yang
 * dipegang pelapor, dan ia tidak mengikat ke identitas siapa pun. Lampiran dan lokasi tetap
 * opsional — laporan tanpa keduanya sama sahnya.
 */
export function ReportForm({ options }: { options: ReportOptions }) {
  const [state, action, pending] = useActionState<SubmitState, FormData>(submitReport, {
    status: "idle",
  });

  if (state.status === "sent") {
    return (
      <div className="warga-card flex flex-col gap-4 p-7 sm:p-9" role="status">
        <span
          className="inline-flex h-16 w-16 items-center justify-center bg-[#DCFCE7] text-2xl text-[#166534]"
          aria-hidden="true"
        >
          ✓
        </span>
        <h2 className="text-[28px] text-[rgb(var(--warga-navy))]">Laporan terkirim</h2>
        <p className="text-base leading-relaxed text-ink-faint">
          Simpan nomor tiket berikut. Nomor ini satu-satunya penanda laporan Anda — tidak ada nama
          atau nomor telepon yang tersimpan.
        </p>
        <div className="flex flex-wrap gap-3">
          <div className="flex-[2_1_260px] bg-base-950 px-4 py-4">
            <p className="text-[13px] text-ink-faint">Nomor tiket</p>
            <p className="mt-0.5 font-mono text-xl font-extrabold tracking-wider text-[rgb(var(--warga-navy))]">
              {state.ticket}
            </p>
          </div>
        </div>
        <p className="text-sm leading-relaxed text-ink-muted">{state.message}</p>
        <p className="text-xs leading-relaxed text-ink-faint">{state.basis}</p>
        <div className="flex flex-wrap gap-2.5">
          <Link href="/lapor" className="warga-btn warga-btn-primary">
            Buat laporan lain
          </Link>
          <Link href="/" className="warga-btn warga-btn-ghost">
            Halaman muka
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form action={action} className="flex flex-col gap-4">
      {state.status === "error" ? (
        <p role="alert" className="warga-error">
          {state.message}
        </p>
      ) : null}

      <fieldset className="warga-fieldset">
        <legend className="warga-legend-step">
          <i>1</i>Jenis kejadian
        </legend>
        <div
          className="clear-both grid gap-2.5 sm:grid-cols-2"
          role="radiogroup"
          aria-label="Jenis kejadian"
        >
          {options.categories.map((category) => (
            <label key={category} className="warga-option relative">
              <input type="radio" name="category" value={category} required />
              <span className="text-base font-bold">{category}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="warga-fieldset">
        <legend className="warga-legend-step">
          <i>2</i>Waktu &amp; lokasi
        </legend>
        <div className="clear-both flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="warga-label">
              Waktu kejadian <span className="font-medium text-ink-faint">(opsional)</span>
            </span>
            <input type="datetime-local" name="incident_time" className="warga-field max-w-xs" />
            <span className="warga-help">
              Dikosongkan berarti kejadiannya sedang berlangsung atau baru saja terjadi.
            </span>
          </label>
          <AreaPicker areas={options.areas ?? []} kecamatanList={options.kecamatan} />
          <label className="flex flex-col gap-1.5">
            <span className="warga-label">
              Alamat atau patokan <span className="font-medium text-ink-faint">(opsional)</span>
            </span>
            <input
              type="text"
              name="location_text"
              maxLength={255}
              placeholder="Contoh: depan minimarket, gang samping pasar, dekat halte"
              className="warga-field"
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="warga-fieldset">
        <legend className="warga-legend-step">
          <i>3</i>Kronologi
        </legend>
        <div className="clear-both flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="warga-label">Uraian kejadian</span>
            <textarea
              name="description"
              required
              rows={5}
              minLength={10}
              maxLength={options.max_description}
              placeholder="Uraikan secara berurutan: apa yang Anda lihat, kapan Anda mengetahui kejadian, serta ciri pelaku apabila ada."
              className="warga-field"
            />
            <span className="warga-help">
              <strong>Jangan menuliskan nama, nomor telepon, atau alamat siapa pun</strong> —
              termasuk nama Anda sendiri. Sistem ini tidak menyimpan identitas.
            </span>
          </label>
          <AttachFiles options={options} />
        </div>
      </fieldset>

      <div className="warga-fieldset flex flex-wrap items-center justify-between gap-4">
        <label className="flex min-h-[44px] flex-[1_1_300px] items-center gap-2.5 text-sm">
          <input
            type="checkbox"
            required
            className="h-5 w-5 flex-none accent-[rgb(var(--warga-navy))]"
          />
          Saya menyatakan bahwa informasi ini benar sesuai dengan yang saya ketahui.
        </label>
        <button
          type="submit"
          disabled={pending}
          className="warga-btn warga-btn-primary min-h-[54px] px-8 disabled:opacity-50"
        >
          {pending ? "Mengirim…" : "Kirim laporan"}
        </button>
        <Basis className="basis-full">{options.coordinate_basis}</Basis>
      </div>
    </form>
  );
}
