"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavIcon } from "./icons";
import { NAV_ITEMS } from "./navigation";

/**
 * Sidebar ikon + label, mengikuti referensi visual.
 *
 * Menu ditampilkan seluruhnya; pembatasan menurut permission dipasang setelah
 * RBAC hidup (TASK 052). Menyembunyikan menu **bukan** pengganti otorisasi —
 * backend tetap yang memutuskan (CLAUDE.md §15).
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Navigasi utama"
      className="flex w-[92px] shrink-0 flex-col items-center gap-1 border-r border-base-800 bg-base-900/60 py-3"
    >
      {NAV_ITEMS.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={[
              "group flex w-[76px] flex-col items-center gap-1.5 rounded-md px-1 py-2.5 transition-colors",
              active
                ? "bg-accent/10 text-accent shadow-glow"
                : "text-ink-muted hover:bg-base-800/70 hover:text-ink",
            ].join(" ")}
          >
            <NavIcon name={item.icon} />
            <span className="text-center text-[9px] font-semibold uppercase leading-tight tracking-wider">
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
