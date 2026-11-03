import Link from "next/link";
import { PolriEmblem } from "@/components/warga/brand";
import { WargaBottomNav, WargaTopNav } from "@/components/warga/nav";

/**
 * SIGAP WARGA — kerangka halaman masyarakat (2 November 2026; rupa papan pengumuman
 * 3 November 2026).
 *
 * Satu pembungkus `.warga` mengganti seluruh token warna menjadi tema gelap-hangat dengan
 * garis-garis 1px, sehingga sisi masyarakat tidak pernah tampak seperti sisi kepolisian
 * (/ops) dan tidak terpengaruh pengalih gelap/terang di sana.
 *
 * Kepala halaman dua baris, meniru situs lembaga dan ruang berita: strip tipis gelap
 * berisi nama satuan dan tautan darurat, lalu masthead berisi lambang, wordmark
 * berkotak emas, dan tautan teks condensed bergaris bawah emas bila aktif. Tidak ada pil,
 * tidak ada tombol berwarna di dalam navigasi. Di ponsel navigasi turun ke bawah.
 */
export default function WargaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="warga min-h-screen bg-base-950 text-ink">
      <div className="warga-strip">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4">
          <span className="truncate">
            Polres Metro Jakarta Selatan <span className="warga-strip-sep">·</span> Polri bersama
            masyarakat
          </span>
          <span className="ml-auto flex shrink-0 items-center gap-4">
            <a href="tel:110" className="warga-strip-link">
              Darurat 110
            </a>
            <Link href="/ops/masuk" className="warga-strip-link hidden sm:inline">
              Masuk petugas
            </Link>
          </span>
        </div>
      </div>

      <header className="warga-masthead sticky top-0 z-30">
        <div className="mx-auto flex max-w-6xl items-stretch gap-5 px-4">
          <Link href="/" className="flex items-center gap-3 py-2.5">
            <PolriEmblem size={36} className="h-9 w-9" />
            <span className="warga-wordmark">SIGAP WARGA</span>
          </Link>
          <nav aria-label="Navigasi warga" className="ml-auto hidden items-stretch sm:flex">
            <WargaTopNav />
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-24 pt-5 sm:pb-12">{children}</main>

      <footer className="warga-footer hidden sm:block">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 text-xs sm:grid-cols-[auto_1fr_auto]">
          <PolriEmblem size={40} className="h-10 w-10" />
          <div className="leading-relaxed text-ink-muted">
            <p className="font-semibold text-ink">SIGAP WARGA</p>
            <p>
              Sistem Inteligensi Geospasial dan Analitik Prediktif · Polres Metro Jakarta Selatan.
              Angka di situs ini adalah ringkasan historis per wilayah, bukan ramalan untuk
              perorangan.
            </p>
          </div>
          <ul className="space-y-1 text-ink-muted sm:text-right">
            <li>
              <a href="tel:110" className="warga-link">
                Darurat 110
              </a>
            </li>
            <li>
              <Link href="/lapor" className="warga-link">
                Lapor kejadian
              </Link>
            </li>
            <li>
              <Link href="/ops/masuk" className="warga-link">
                Masuk petugas
              </Link>
            </li>
          </ul>
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
