import Link from "next/link";

export type ScreenTab = {
  href: string;
  label: string;
  /** Tab tampil bila pengguna memegang permission ini; kosong = selalu tampil. */
  permission?: string;
};

/**
 * Tab antar-layar serumpun (12 November 2026, peringkasan menu /ops — catatan 179).
 *
 * Layar yang keluar dari menu (Pola, Peringkat, Input Data, Pembakuan) tetap dapat dicapai
 * sebagai tab di atas layar induknya: Analitik ⇄ Pola, Produk Bulanan ⇄ Peringkat, Laporan
 * Petugas ⇄ Catat kejadian ⇄ Pembakuan. Tab disaring menurut permission yang dipegang —
 * kenyamanan, bukan otorisasi; backend tetap memeriksa setiap permintaan (CLAUDE.md §15).
 */
export function ScreenTabs({
  tabs,
  current,
  permissions = [],
}: {
  tabs: readonly ScreenTab[];
  /** Rute layar yang sedang dibuka (tanpa query). */
  current: string;
  permissions?: readonly string[];
}) {
  const shown = tabs.filter((tab) => !tab.permission || permissions.includes(tab.permission));
  if (shown.length < 2) return null;
  return (
    <nav aria-label="Layar serumpun" className="flex flex-wrap gap-1 border-b border-base-800">
      {shown.map((tab) => {
        const path = tab.href.split("?")[0];
        const active = path === current;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`-mb-px border-b-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
              active
                ? "border-accent text-accent"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
