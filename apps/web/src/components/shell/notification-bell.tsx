"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { NotificationFeed } from "@/lib/notifications";

/**
 * Lonceng antrean pekerjaan di pojok kanan atas.
 *
 * Isinya **berbeda menurut peran**, dan perbedaannya ditentukan backend: tiap sumber
 * terikat ke permission tindakan, bukan permission baca. Seorang Pimpinan melihat
 * rekomendasi yang menunggu keputusannya; petugas Polsek melihat peringatan yang belum
 * diterima dan laporan warga yang belum diverifikasi. Yang tidak dapat dikerjakan seseorang
 * tidak muncul padanya.
 *
 * ## Angka yang tidak pernah bohong
 *
 * Tidak ada penanda "sudah dibaca". Jumlahnya dihitung ulang dari keadaan sebenarnya setiap
 * kali halaman dimuat, sehingga lencana menjadi **nol ketika pekerjaannya benar-benar
 * selesai** — dan angka nol itulah yang membuat angka bukan-nol berarti sesuatu. Penanda
 * terbaca akan mengubahnya menjadi angka yang dapat dihilangkan tanpa mengerjakan apa pun.
 *
 * ## Mengapa komponen klien
 *
 * Isinya dimuat di server dan diberikan sebagai prop; yang berjalan di peramban hanya
 * buka-tutup panelnya. Datanya sendiri tidak pernah diambil dari sisi peramban.
 */
export function NotificationBell({ feed }: { feed: NotificationFeed }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  // Menutup panel saat pengguna menekan di luarnya atau menekan Escape. Tanpa keduanya,
  // panel yang terbuka menutupi isi halaman dan satu-satunya jalan keluar adalah menekan
  // lonceng lagi — yang tidak terpikirkan orang saat panelnya menghalangi.
  useEffect(() => {
    if (!open) return;

    const onPointer = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const waiting = feed.total > 0;

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={
          waiting ? `${feed.total} pekerjaan menunggu Anda` : "Tidak ada pekerjaan yang menunggu"
        }
        className={`relative flex items-center gap-1.5 rounded border px-2.5 py-1.5 transition-colors ${
          waiting
            ? "border-risk-critical/50 bg-risk-critical/10 text-risk-critical hover:bg-risk-critical/20"
            : "border-base-700 text-ink-muted hover:border-accent/40 hover:text-accent"
        }`}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
        >
          <path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" />
          <path d="M10.3 20a2 2 0 0 0 3.4 0" />
        </svg>
        <span className="font-mono text-[11px] font-bold tabular-nums">{feed.total}</span>
      </button>

      {open ? (
        <div className="absolute right-0 z-30 mt-1.5 w-[320px] rounded border border-base-700 bg-base-900 shadow-panel">
          <div className="flex items-baseline gap-2 border-b border-base-800 px-3 py-2">
            <span className="stat-label">Menunggu Anda</span>
            <span className="ml-auto text-[10px] text-ink-faint">{feed.role}</span>
          </div>

          <div className="max-h-[62vh] overflow-y-auto">
            {feed.groups.length === 0 ? (
              <p className="px-3 py-4 text-[11px] leading-relaxed text-ink-muted">
                Peran Anda tidak memiliki antrean pekerjaan pada sistem ini. Itu bukan kekeliruan —
                kewenangan Anda membaca dan menganalisis, bukan menyetujui atau menriase.
              </p>
            ) : (
              feed.groups.map((group) => (
                <div key={group.kind} className="border-b border-base-800 last:border-b-0">
                  <Link
                    href={group.href}
                    onClick={() => setOpen(false)}
                    className="block px-3 py-2.5 transition-colors hover:bg-base-800/60"
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="text-[11px] font-semibold text-ink">{group.title}</span>
                      <span
                        className={`ml-auto font-mono text-xs font-bold tabular-nums ${
                          group.total > 0 ? "text-risk-critical" : "text-ink-faint"
                        }`}
                      >
                        {group.total}
                      </span>
                    </div>
                    <div className="text-[10px] text-ink-faint">{group.action}</div>

                    {group.items.length > 0 ? (
                      <ul className="mt-1.5 space-y-1">
                        {group.items.map((item) => (
                          <li key={item.code} className="text-[10px] leading-tight">
                            <span className="text-ink-muted">{item.headline}</span>
                            <span className="block text-ink-faint">{item.detail}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      // Antrean kosong tetap ditampilkan: "nol peringatan menunggu" adalah
                      // kabar baik, dan menghilangkan barisnya membuat pembaca tidak dapat
                      // membedakan "tidak ada" dari "tidak diperiksa".
                      <p className="mt-1 text-[10px] text-ink-faint">Tidak ada yang menunggu.</p>
                    )}
                  </Link>
                </div>
              ))
            )}
          </div>

          <p className="border-t border-base-800 px-3 py-2 text-[9px] leading-relaxed text-ink-faint">
            Daftar ini dihitung ulang setiap halaman dimuat. Tidak ada penanda "sudah dibaca" —
            angkanya hanya turun ketika pekerjaannya selesai.
          </p>
        </div>
      ) : null}
    </div>
  );
}
