import Link from "next/link";
import { getReportOptions } from "./actions";
import { ReportForm } from "./report-form";

export const metadata = { title: "Lapor Kejadian — SIGAP WARGA" };

// Pilihan isian diambil dari API saat halaman dibuka, bukan saat build: daftar kecamatan
// berasal dari master lokasi, dan API tidak dapat dihubungi ketika image sedang dibangun.
export const dynamic = "force-dynamic";

/**
 * Halaman laporan masyarakat (mockup 10 November 2026). **Terbuka tanpa akun.**
 *
 * Spanduk merah untuk keadaan darurat di paling atas, judul "Lapor kejadian", lalu formulir
 * bertahap (1 Jenis kejadian · 2 Waktu & lokasi · 3 Kronologi). Bentuknya mengikuti
 * `docs/14` §3: pengiriman tanpa akun, tanpa identitas, dengan nomor tiket acak sebagai
 * satu-satunya penanda — blok "Kontak pelapor" pada mockup sengaja TIDAK dibangun (U-13).
 */
export default async function LaporPage() {
  const options = await getReportOptions();

  return (
    <div>
      <div className="warga-banner">
        <div className="warga-wrap flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-3.5">
          <span className="text-[15px] font-semibold">
            Apabila kejadian sedang berlangsung atau terdapat korban luka, jangan mengisi formulir
            ini. Segera hubungi 110.
          </span>
          <a href="tel:110" className="warga-btn warga-btn-sm">
            Telepon 110 sekarang
          </a>
        </div>
      </div>

      <section className="warga-wrap pb-4 pt-10">
        <p className="warga-eyebrow">Laporan Masyarakat</p>
        <h1 className="mt-2 text-4xl text-[rgb(var(--warga-navy))] sm:text-[44px]">
          Lapor kejadian
        </h1>
        <p className="mt-2.5 max-w-[720px] text-[17px] leading-relaxed text-ink-faint">
          Lengkapi formulir berikut untuk membuat laporan. Anda juga dapat melapor secara langsung
          ke{" "}
          <strong className="text-[rgb(var(--warga-navy))]">
            SPKT Polres Metro Jakarta Selatan
          </strong>{" "}
          · buka 24 jam. Laporan di sini bukan pengganti laporan polisi resmi.
        </p>
      </section>

      <section className="warga-wrap pb-16 pt-4">
        <ReportForm options={options} />
        <div className="mt-5 space-y-2 text-xs leading-relaxed text-ink-faint">
          <p>
            <strong className="text-ink-muted">Tanpa akun dan tanpa identitas.</strong> Sistem ini
            tidak meminta dan tidak menyimpan nama, nomor telepon, maupun alamat pelapor.
          </p>
          <p>{options.intake_basis}</p>
          <p>
            <Link href="/ops/masuk" className="warga-link">
              Masuk sebagai petugas
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
