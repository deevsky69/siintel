"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/**
 * Keadaan gagal layar laporan intelijen (CLAUDE.md §23).
 *
 * Kewenangan yang tidak dimiliki **tidak** sampai ke sini: halaman memeriksanya lebih dulu
 * dan menampilkan penjelasannya sendiri. Yang tersisa untuk layar ini adalah kegagalan
 * yang sesungguhnya — backend tidak terjangkau, sesi habis, atau permintaan ditolak karena
 * akun dibatasi wilayah tetapi belum memiliki penetapan Polsek. Sebabnya tidak ditebak di
 * sini: menuliskan salah satu sebagai sebab akan menyesatkan.
 */
export default function IntelligenceError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel title="Laporan Intelijen">
      <ErrorState label="Laporan intelijen gagal dimuat." />
      <div className="mt-3 text-center">
        <button
          type="button"
          onClick={reset}
          className="rounded border border-base-800 px-3 py-1.5 font-heading text-[11px] font-semibold uppercase tracking-wider text-ink hover:border-accent/60 hover:text-accent"
        >
          Coba muat ulang
        </button>
      </div>
    </Panel>
  );
}
