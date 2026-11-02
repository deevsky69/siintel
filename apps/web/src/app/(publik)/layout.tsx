import Link from "next/link";

/**
 * SIGAP WARGA — kerangka halaman masyarakat (2 November 2026).
 *
 * Satu pembungkus `.warga` mengganti seluruh token warna menjadi tema terang yang hangat,
 * sehingga sisi masyarakat tidak pernah tampak seperti sisi kepolisian (/ops) dan tidak
 * terpengaruh pengalih gelap/terang di sana. Navigasi: empat tujuan saja — Beranda, Peta,
 * Survey, Lapor — di atas pada layar lebar, di bawah pada ponsel.
 */
const NAV = [
  { href: "/", label: "Beranda", icon: "⌂" },
  { href: "/peta", label: "Peta", icon: "◎" },
  { href: "/survey", label: "Survey", icon: "★" },
  { href: "/lapor", label: "Lapor", icon: "✎" },
] as const;

export default function WargaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="warga min-h-screen bg-base-950 text-ink">
      <header className="sticky top-0 z-30 border-b border-base-800 bg-base-900/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent font-bold text-white">
              S
            </span>
            <span className="leading-tight">
              <span className="block text-sm font-bold tracking-tight text-ink">SIGAP WARGA</span>
              <span className="block text-[11px] text-ink-muted">Polres Metro Jakarta Selatan</span>
            </span>
          </Link>
          <nav aria-label="Navigasi warga" className="ml-auto hidden items-center gap-1 sm:flex">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-full px-3.5 py-1.5 text-sm font-medium text-ink-muted transition hover:bg-base-850 hover:text-ink"
              >
                {item.label}
              </Link>
            ))}
            <a href="tel:110" className="warga-btn warga-btn-danger ml-2 !px-4 !py-1.5 !text-sm">
              Darurat 110
            </a>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-4 pb-24 pt-5 sm:pb-10">{children}</main>

      <footer className="hidden border-t border-base-800 py-6 text-center text-xs text-ink-faint sm:block">
        SIGAP WARGA · Sistem Inteligensi Geospasial dan Analitik Prediktif · Polres Metro Jakarta
        Selatan ·{" "}
        <Link href="/ops/masuk" className="underline hover:text-ink-muted">
          Masuk petugas
        </Link>
      </footer>

      <nav
        aria-label="Navigasi bawah"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-base-800 bg-base-900/95 backdrop-blur sm:hidden"
      >
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium text-ink-muted"
          >
            <span className="text-lg leading-none" aria-hidden="true">
              {item.icon}
            </span>
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
