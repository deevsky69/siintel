/**
 * Keadaan data baku: memuat, kosong, gagal.
 *
 * CLAUDE.md §23 mensyaratkan setiap halaman memiliki keadaan Loading, Empty, dan Error —
 * disediakan sekali di sini supaya seluruh layar memakai bentuk yang sama.
 */
export function LoadingState({ label = "Memuat data…" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center gap-2 text-sm text-ink-muted">
      <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
      {label}
    </div>
  );
}

export function EmptyState({ label = "Belum ada data." }: { label?: string }) {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center text-sm text-ink-muted">
      {label}
    </div>
  );
}

export function ErrorState({ label = "Data gagal dimuat." }: { label?: string }) {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center text-sm text-risk-critical">
      {label}
    </div>
  );
}
