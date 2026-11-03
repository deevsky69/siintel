import Link from "next/link";
import { PolriEmblem } from "@/components/warga/brand";
import { WargaBottomNav, WargaTopNav } from "@/components/warga/nav";

/**
 * SIGAP WARGA — kerangka halaman masyarakat (2 November 2026; rupa baru 3 November 2026).
 *
 * Satu pembungkus `.warga` mengganti seluruh token warna menjadi tema terang yang hangat,
 * sehingga sisi masyarakat tidak pernah tampak seperti sisi kepolisian (/ops) dan tidak
 * terpengaruh pengalih gelap/terang di sana. Navigasi: lima tujuan — Beranda, Peta,
 * Survey, Lacak, Lapor — di atas pada layar lebar, di bawah pada ponsel. Lambang Polri di
 * kepala halaman; perpindahan rute dianimasikan oleh template.tsx.
 */
export default function WargaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="warga min-h-screen bg-base-950 text-ink">
      <header className="sticky top-0 z-30 border-b border-base-800 bg-base-900/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5">
          <Link href="/" className="flex items-center gap-2.5">
            <PolriEmblem size={40} className="h-10 w-10" />
            <span className="leading-tight">
              <span className="font-display block text-[15px] font-extrabold tracking-tight text-ink">
                SIGAP WARGA
              </span>
              <span className="block text-[11px] text-ink-muted">Polres Metro Jakarta Selatan</span>
            </span>
          </Link>
          <nav aria-label="Navigasi warga" className="ml-auto hidden items-center gap-1 sm:flex">
            <WargaTopNav />
            <a href="tel:110" className="warga-btn warga-btn-danger ml-2 !px-4 !py-1.5 !text-sm">
              Darurat 110
            </a>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-24 pt-5 sm:pb-10">{children}</main>

      <footer className="hidden border-t border-base-800 py-8 sm:block">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 text-xs text-ink-faint">
          <PolriEmblem size={32} className="h-8 w-8 opacity-80" />
          <p className="leading-relaxed">
            <span className="font-semibold text-ink-muted">Polri bersama masyarakat.</span> SIGAP
            WARGA · Sistem Inteligensi Geospasial dan Analitik Prediktif · Polres Metro Jakarta
            Selatan
          </p>
          <Link href="/ops/masuk" className="ml-auto underline hover:text-ink-muted">
            Masuk petugas
          </Link>
        </div>
      </footer>

      <nav
        aria-label="Navigasi bawah"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-base-800 bg-base-900/95 backdrop-blur sm:hidden"
      >
        <WargaBottomNav />
      </nav>
    </div>
  );
}
