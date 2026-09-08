import Link from "next/link";
import { getReportOptions } from "./actions";
import { ReportForm } from "./report-form";

export const metadata = { title: "Lapor Kejadian — PREDIKSI PRESISI" };

// Pilihan isian diambil dari API saat halaman dibuka, bukan saat build: daftar kecamatan
// berasal dari master lokasi, dan API tidak dapat dihubungi ketika image sedang dibangun.
export const dynamic = "force-dynamic";

/**
 * Halaman laporan masyarakat (TASK 160). **Terbuka tanpa akun.**
 *
 * Bentuknya mengikuti `docs/14` §3: pengiriman tanpa akun, tanpa identitas, dengan nomor
 * tiket acak sebagai satu-satunya penanda.
 */
export default async function LaporPage() {
  const options = await getReportOptions();

  return (
    <main className="mx-auto min-h-screen w-full max-w-lg p-6">
      <div className="mb-6 text-center">
        <Link href="/" className="inline-block">
          <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg border border-accent/30 bg-accent/10 font-heading text-base font-bold text-accent">
            PP
          </span>
        </Link>
        <h1 className="font-heading text-xl font-bold tracking-wide text-ink">Lapor Kejadian</h1>
        <p className="mt-1 text-xs uppercase tracking-[0.14em] text-ink-muted">
          Polres Metro Jakarta Selatan
        </p>
      </div>

      {/* Ditempatkan SEBELUM formulir, bukan sesudahnya. Orang yang sedang menghadapi
          keadaan darurat tidak akan membaca catatan kaki di bawah tombol kirim. */}
      <p className="mb-5 rounded border border-risk-critical/40 bg-risk-critical/10 px-3 py-2.5 text-xs leading-relaxed text-ink">
        <strong className="text-risk-critical">Sedang darurat? Hubungi 110.</strong> Halaman ini
        untuk laporan yang tidak memerlukan penanganan seketika. Laporan di sini{" "}
        <strong>bukan pengganti laporan polisi resmi</strong>.
      </p>

      <ReportForm options={options} />

      <div className="mt-5 space-y-2 text-xs leading-relaxed text-ink-faint">
        <p>
          <strong className="text-ink-muted">Tanpa akun dan tanpa identitas.</strong> Sistem ini
          tidak meminta dan tidak menyimpan nama, nomor telepon, maupun alamat pelapor.
        </p>
        <p>{options.intake_basis}</p>
        <p>
          <Link href="/masuk" className="underline hover:text-ink-muted">
            Masuk sebagai petugas
          </Link>
        </p>
      </div>
    </main>
  );
}
