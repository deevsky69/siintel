"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { NavIcon } from "./icons";
import type { NavItem } from "./navigation";
import { groupOf, visibleNavGroups } from "./navigation";

/**
 * Sidebar berkelompok dengan submenu yang dapat dibuka-tutup.
 *
 * **Menyembunyikan menu bukan pengganti otorisasi.** Backend tetap memutuskan setiap
 * permintaan, dan membuka alamat yang tersembunyi tetap dijawab sebagaimana mestinya
 * (CLAUDE.md §15). Yang dikerjakan di sini semata mengurangi apa yang harus dibaca.
 *
 * **Hanya kelompok yang sedang aktif yang terbuka.** Membuka seluruhnya mengembalikan
 * persoalan yang justru hendak diselesaikan susunan ini: dua puluh baris setara yang harus
 * dibaca semuanya untuk menemukan satu. Kelompok lain cukup satu klik.
 *
 * Kelompok yang dibuka pengguna **ditambahkan**, bukan menggantikan yang aktif: menutup
 * kelompok tempat halaman yang sedang dibuka berada akan menghilangkan penanda posisi, dan
 * pengguna kehilangan jejak di mana ia berada.
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
  const groups = visibleNavGroups(permissions);
  const activeGroup = groupOf(pathname);

  /** Kelompok yang dibuka sendiri oleh pengguna, di luar yang sedang aktif. */
  const [opened, setOpened] = useState<Set<string>>(new Set());

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  const toggle = (id: string) =>
    setOpened((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <nav
      aria-label="Navigasi utama"
      className="flex w-[196px] shrink-0 flex-col gap-0.5 overflow-y-auto border-r border-base-800 bg-base-900/60 px-2 py-3"
    >
      {groups.map((group) => {
        const open = group.id === activeGroup ? !opened.has(group.id) : opened.has(group.id);
        const badge = group.items.some((item) => item.href === "/rekomendasi")
          ? pendingDecisions
          : 0;

        return (
          <div key={group.id}>
            <button
              type="button"
              onClick={() => toggle(group.id)}
              aria-expanded={open}
              className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left transition-colors ${
                group.id === activeGroup
                  ? "text-accent"
                  : "text-ink-muted hover:bg-base-800/70 hover:text-ink"
              }`}
            >
              <NavIcon name={group.icon} className="h-4 w-4 shrink-0" />
              <span className="flex-1 font-heading text-[11px] font-semibold uppercase tracking-wider">
                {group.label}
              </span>
              {/* Lencana pindah ke judul kelompok saat submenunya tertutup, supaya
                  keputusan yang menunggu tetap terlihat tanpa harus membuka apa pun. */}
              {badge > 0 && !open ? (
                <span
                  aria-hidden="true"
                  className="min-w-[16px] rounded-full bg-risk-critical px-1 text-center font-mono text-[9px] font-bold leading-4 text-base-950"
                >
                  {badge > 99 ? "99+" : badge}
                </span>
              ) : null}
              <span
                aria-hidden="true"
                className={`text-[9px] transition-transform ${open ? "rotate-90" : ""}`}
              >
                &#9656;
              </span>
            </button>

            {open ? (
              <ul className="mb-1 ml-[13px] border-l border-base-800 pl-2">
                {group.items.map((item) => (
                  <li key={item.href}>
                    <SubmenuLink
                      item={item}
                      active={isActive(item.href)}
                      badge={item.href === "/rekomendasi" ? pendingDecisions : 0}
                    />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}

function SubmenuLink({ item, active, badge }: { item: NavItem; active: boolean; badge: number }) {
  return (
    <Link
      href={item.href}
      title={item.hint}
      aria-current={active ? "page" : undefined}
      className={`flex items-center gap-2 rounded px-2 py-1.5 text-[11px] leading-tight transition-colors ${
        active
          ? "bg-accent/10 font-semibold text-accent"
          : "text-ink-muted hover:bg-base-800/70 hover:text-ink"
      }`}
    >
      <span className="flex-1">{item.label}</span>
      {badge > 0 ? (
        <>
          <span
            aria-hidden="true"
            className="min-w-[16px] rounded-full bg-risk-critical px-1 text-center font-mono text-[9px] font-bold leading-4 text-base-950"
          >
            {badge > 99 ? "99+" : badge}
          </span>
          <span className="sr-only">{badge} rekomendasi menunggu keputusan Anda</span>
        </>
      ) : null}
    </Link>
  );
}
