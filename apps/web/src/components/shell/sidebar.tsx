"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavIcon } from "./icons";
import { groupedNavItems } from "./navigation";

/**
 * Sidebar ikon + label, dikelompokkan menurut kata kerja.
 *
 * **Menyembunyikan menu bukan pengganti otorisasi.** Backend tetap memutuskan setiap
 * permintaan, dan membuka alamat yang tersembunyi tetap dijawab sebagaimana mestinya
 * (CLAUDE.md §15). Yang dikerjakan di sini semata mengurangi apa yang harus dibaca:
 * sebelumnya keenambelas menu tampil kepada semua peran, dan seorang Pimpinan yang membuka
 * `Input Data` atau `Admin` hanya disambut kalimat "Akun Anda tidak memiliki kewenangan".
 *
 * Lencana pada `Keputusan` hanya muncul bagi pemegang `commander_decision:approve`. Bagi
 * peran lain, rekomendasi yang menunggu bukan pekerjaan mereka, dan angka merah yang tidak
 * dapat mereka selesaikan hanya menjadi kecemasan tanpa jalan keluar.
 */
export function Sidebar({
  permissions,
  pendingDecisions = 0,
}: {
  permissions: readonly string[];
  /** Rekomendasi yang menunggu keputusan; 0 berarti lencana tidak digambar. */
  pendingDecisions?: number;
}) {
  const pathname = usePathname();
  const sections = groupedNavItems(permissions);

  return (
    <nav
      aria-label="Navigasi utama"
      className="flex w-[92px] shrink-0 flex-col items-center gap-1 overflow-y-auto border-r border-base-800 bg-base-900/60 py-3"
    >
      {sections.map((section, index) => (
        <div key={section.group} className="flex w-full flex-col items-center">
          {/* Pemisah kelompok pertama tidak digambar: garis di puncak sidebar hanya
              menambah coretan tanpa memisahkan apa pun. */}
          {index > 0 ? <span className="my-1.5 h-px w-12 bg-base-800" /> : null}
          <span className="mb-1 text-[8px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
            {section.label}
          </span>

          {section.items.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const badge = item.href === "/rekomendasi" ? pendingDecisions : 0;

            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "group relative flex w-[76px] flex-col items-center gap-1.5 rounded-md px-1 py-2.5 transition-colors",
                  active
                    ? "bg-accent/10 text-accent shadow-glow"
                    : "text-ink-muted hover:bg-base-800/70 hover:text-ink",
                ].join(" ")}
              >
                <NavIcon name={item.icon} />
                {badge > 0 ? (
                  <span
                    // Jumlahnya ikut dibaca pembaca layar lewat teks tersembunyi di bawah,
                    // sehingga lencana visual ini tidak perlu diumumkan dua kali.
                    aria-hidden="true"
                    className="absolute right-2.5 top-1.5 min-w-[16px] rounded-full bg-risk-critical px-1 text-center font-mono text-[9px] font-bold leading-4 text-base-950"
                  >
                    {badge > 99 ? "99+" : badge}
                  </span>
                ) : null}
                <span className="text-center text-[9px] font-semibold uppercase leading-tight tracking-wider">
                  {item.label}
                </span>
                {badge > 0 ? (
                  <span className="sr-only">{badge} rekomendasi menunggu keputusan Anda</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
