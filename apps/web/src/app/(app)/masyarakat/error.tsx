"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/**
 * Keadaan gagal Community Signal Dashboard (CLAUDE.md §23).
 *
 * Termasuk keadaan tidak berwenang: peran tanpa `citizen_report:read` ditolak backend, dan
 * penolakan itu sampai ke sini sebagai kegagalan pemuatan. Pesannya sengaja tidak
 * membedakan keduanya — menyebut "Anda tidak berwenang" akan menegaskan bahwa datanya ada.
 */
export default function CommunityError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel title="Sinyal Masyarakat">
      <ErrorState label="Laporan masyarakat gagal dimuat atau tidak tersedia untuk akun Anda." />
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
