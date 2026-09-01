import { Clock } from "./clock";

/**
 * Topbar: identitas sistem, satuan wilayah, jam WIB, dan pengguna aktif.
 *
 * Identitas pengguna masih placeholder sampai autentikasi hidup (TASK 050);
 * ditandai jelas agar tidak terbaca sebagai data nyata.
 */
export function Topbar() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-6 border-b border-base-800 bg-base-900/70 px-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-accent/30 bg-accent/10 font-heading text-sm font-bold text-accent">
          PP
        </div>
        <div className="leading-tight">
          <div className="font-heading text-base font-bold tracking-wide text-ink">
            PREDIKSI PRESISI
          </div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">
            Predictive Policing &amp; Spatial Intelligence System
          </div>
        </div>
      </div>

      <div className="hidden flex-1 justify-center lg:flex">
        <div className="font-heading text-lg font-bold uppercase tracking-[0.16em] text-ink">
          Polres Metro Jakarta Selatan
        </div>
      </div>

      <div className="ml-auto flex items-center gap-5">
        <Clock />
        <div className="flex items-center gap-2.5 border-l border-base-800 pl-5">
          <div className="text-right leading-tight">
            <div className="text-xs font-semibold text-ink">Pengguna Demo</div>
            <div className="text-[10px] text-ink-muted">belum masuk — TASK 050</div>
          </div>
          <div className="h-8 w-8 rounded-full border border-base-700 bg-base-800" />
        </div>
      </div>
    </header>
  );
}
