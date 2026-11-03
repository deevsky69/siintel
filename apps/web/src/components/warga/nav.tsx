"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export const WARGA_NAV = [
  { href: "/", label: "Beranda", icon: "home" },
  { href: "/peta", label: "Peta", icon: "map" },
  { href: "/survey", label: "Survey", icon: "star" },
  { href: "/lacak", label: "Lacak", icon: "search" },
  { href: "/lapor", label: "Lapor", icon: "pen" },
] as const;

type Icon = (typeof WARGA_NAV)[number]["icon"];

const PATHS: Record<Icon, string> = {
  home: "M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  map: "M9 4 3 6.5v13L9 17l6 2.5 6-2.5v-13L15 6.5zm0 0v13m6-10.5v13",
  star: "m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z",
  search: "M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zm5 11.5L20 20",
  pen: "M4 20h4l10.5-10.5a2 2 0 0 0 0-2.8l-1.2-1.2a2 2 0 0 0-2.8 0L4 16z",
};

function NavIcon({ name }: { name: Icon }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

function isCurrent(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** Navigasi atas (layar lebar): pil biru menandai halaman yang sedang dibuka. */
export function WargaTopNav() {
  const pathname = usePathname();
  return (
    <>
      {WARGA_NAV.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="warga-nav-link"
          aria-current={isCurrent(pathname, item.href) ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
    </>
  );
}

/** Navigasi bawah (ponsel): garis kuning di atas tab yang sedang dibuka. */
export function WargaBottomNav() {
  const pathname = usePathname();
  return (
    <>
      {WARGA_NAV.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="warga-tab flex flex-col items-center gap-0.5 py-2 text-[11px] font-semibold"
          aria-current={isCurrent(pathname, item.href) ? "page" : undefined}
        >
          <NavIcon name={item.icon} />
          {item.label}
        </Link>
      ))}
    </>
  );
}
