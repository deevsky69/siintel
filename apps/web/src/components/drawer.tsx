"use client";

import { type ReactNode, useEffect, useId } from "react";

/**
 * Panel samping (side sheet) untuk formulir dan rincian satu baris tabel.
 *
 * Dipakai layar CRUD (Babinkamtibmas, Laporan Masyarakat — 4 November 2026) supaya tabelnya
 * tetap padat: isian dan uraian panjang tidak pernah menumpuk di dalam baris. Rujukan pola:
 * tabel kontak Attio/Cake Equity dengan side sheet (Refero).
 *
 * Tanpa pustaka tambahan: lapisan latar yang dapat diklik untuk menutup, Escape menutup,
 * `role="dialog"` + `aria-modal` + judul bertaut supaya pembaca layar mengenalinya.
 */
export function Drawer({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Tutup panel"
        onClick={onClose}
        className="absolute inset-0 bg-base-950/70 backdrop-blur-[1px]"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex h-full w-full max-w-md flex-col border-l border-base-800 bg-base-900 shadow-panel"
      >
        <header className="flex items-center justify-between gap-3 border-b border-base-800 px-4 py-3">
          <h2 id={titleId} className="panel-title">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="rounded px-2 py-1 text-sm text-ink-muted hover:bg-base-850 hover:text-ink"
          >
            ✕
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-3">{children}</div>
        {footer ? <footer className="border-t border-base-800 px-4 py-3">{footer}</footer> : null}
      </aside>
    </div>
  );
}
