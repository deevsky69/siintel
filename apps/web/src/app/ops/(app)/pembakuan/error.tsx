"use client";

import { ErrorState } from "@/components/data-state";

export default function PembakuanError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-3">
      <ErrorState label="Antrean pembakuan gagal dimuat." />
      <button
        type="button"
        onClick={reset}
        className="rounded border border-base-700 px-3 py-1.5 text-xs text-ink-muted hover:text-ink"
      >
        Coba lagi
      </button>
    </div>
  );
}
