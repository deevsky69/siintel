import Link from "next/link";
import { PolriEmblem } from "@/components/warga/brand";
import { WargaBottomNav, WargaTopNav } from "@/components/warga/nav";

/**
 * SIGAP WARGA — kerangka halaman masyarakat (rupa lembaga terang, 10 November 2026).
 *
 * Mengikuti mockup "SIGAP WARGA Redesign" pemilik proyek: strip navy berisi nama satuan dan
 * tautan masuk petugas; masthead putih bergaris **emas ganda** dengan lambang, nama dua
 * baris, menu teks bergaris emas, dan dua tombol tetap (Lapor kejadian, Darurat 110); kaki
 * halaman navy. Tidak ada pil, tidak ada sudut membulat. Di ponsel menu turun ke tab bawah.
 *
 * Satu pembungkus `.warga` mengganti seluruh token warna (lihat globals.css), sehingga sisi
 * masyarakat selalu terang dan tidak terpengaruh pengalih gelap/terang milik /ops.
 */
export default function WargaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="warga min-h-screen bg-base-950 text-ink">
      <div className="warga-strip">
        <div className="warga-wrap flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <span>
            Polres Metro Jakarta Selatan <span className="warga-strip-sep">·</span> Polri bersama
            masyarakat
          </span>
          <Link href="/ops/masuk" className="warga-strip-link">
            Masuk petugas →
          </Link>
        </div>
      </div>

      <header className="warga-masthead sticky top-0 z-30">
        <div className="warga-wrap flex flex-wrap items-center justify-between gap-x-8 gap-y-3 py-3">
          <Link href="/" className="warga-brand">
            <PolriEmblem size={96} className="h-[50px] w-auto" />
            <span>
              <b>SIGAP WARGA</b>
              <small>Polres Metro Jakarta Selatan</small>
            </span>
          </Link>
          <nav aria-label="Menu utama" className="hidden flex-wrap gap-1 sm:flex">
            <WargaTopNav />
          </nav>
          <div className="hidden gap-2.5 md:flex">
            <Link href="/lapor" className="warga-btn warga-btn-sm warga-btn-ghost">
              Lapor kejadian
            </Link>
            <a href="tel:110" className="warga-btn warga-btn-sm warga-btn-danger">
              Darurat 110
            </a>
          </div>
        </div>
      </header>

      <main className="w-full pb-24 sm:pb-0">{children}</main>

      <footer className="warga-footer hidden sm:block">
        <div className="warga-wrap flex flex-wrap justify-between gap-8 py-12">
          <div className="flex max-w-md flex-1 basis-80 flex-col gap-3">
            <div className="flex items-center gap-3">
              <PolriEmblem size={96} className="h-[46px] w-auto" />
              <span className="flex flex-col leading-tight">
                <span className="text-xl font-extrabold tracking-wider text-white">
                  SIGAP WARGA
                </span>
                <span className="text-xs font-medium">Polres Metro Jakarta Selatan</span>
              </span>
            </div>
            <p className="text-sm leading-relaxed">
              Sistem Inteligensi Geospasial dan Analitik Prediktif. Angka di situs ini adalah
              ringkasan historis per wilayah, bukan ramalan untuk perorangan.
            </p>
          </div>
          <nav aria-label="Menu footer" className="flex flex-col gap-2.5 text-sm">
            <span className="font-bold text-white">Bantuan</span>
            <a href="tel:110" className="font-bold text-[#FCA5A5]">
              Darurat 110
            </a>
            <Link href="/lapor">Lapor kejadian</Link>
            <Link href="/ops/masuk">Masuk petugas</Link>
          </nav>
        </div>
        <div className="warga-footer-rule">
          <div className="warga-wrap py-5 text-sm font-semibold text-[#E2E8F0]">
            © 2026 Polres Metro Jakarta Selatan · Polri bersama masyarakat
          </div>
        </div>
      </footer>

      <nav
        aria-label="Navigasi bawah"
        className="warga-tabbar fixed inset-x-0 bottom-0 z-30 sm:hidden"
      >
        <WargaBottomNav />
      </nav>
    </div>
  );
}
