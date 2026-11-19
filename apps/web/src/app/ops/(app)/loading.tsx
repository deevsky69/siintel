import { LoadingState } from "@/components/data-state";

/**
 * Keadaan memuat bersama untuk seluruh halaman `/ops` yang belum punya `loading.tsx`
 * sendiri — terutama Beranda, halaman terberat (audit 15 November 2026). Tanpa batas ini,
 * klik menu membekukan halaman lama tanpa tanda apa pun sampai halaman baru selesai
 * dirender di server (CLAUDE.md §23).
 */
export default function Loading() {
  return (
    <div className="space-y-3" aria-busy="true">
      <div className="panel">
        <div className="panel-header">
          <div className="h-3 w-40 animate-pulse rounded bg-base-800" />
        </div>
        <div className="panel-body">
          <LoadingState label="Memuat halaman…" />
        </div>
      </div>
      <div className="grid grid-cols-12 gap-3">
        {[0, 1, 2].map((index) => (
          <div key={index} className="panel col-span-12 xl:col-span-4">
            <div className="panel-header">
              <div className="h-3 w-28 animate-pulse rounded bg-base-800" />
            </div>
            <div className="panel-body space-y-2">
              <div className="h-2.5 w-full animate-pulse rounded bg-base-800/70" />
              <div className="h-2.5 w-5/6 animate-pulse rounded bg-base-800/70" />
              <div className="h-2.5 w-2/3 animate-pulse rounded bg-base-800/70" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
