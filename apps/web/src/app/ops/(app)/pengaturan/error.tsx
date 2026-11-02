"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan gagal (CLAUDE.md §23). */
export default function ScreenError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel title="Pengaturan Sistem">
      <ErrorState label="Konfigurasi gagal dibaca." />
      <p className="mt-2 text-center text-xs text-ink-muted">
        Kewenangan `config:read` diperlukan untuk membaca halaman ini.
      </p>
      <div className="mt-3 text-center">
        <button
          type="button"
          onClick={reset}
          className="rounded border border-base-800 px-3 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider text-ink hover:border-accent/60 hover:text-accent"
        >
          Coba muat ulang
        </button>
      </div>
    </Panel>
  );
}
