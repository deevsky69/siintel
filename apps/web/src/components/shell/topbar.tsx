import { Clock } from "./clock";

/** Topbar: identitas sistem, satuan wilayah, jam WIB, dan pengguna aktif. */
export function Topbar({
  name,
  roleName,
  notifications,
}: {
  name: string;
  roleName: string;
  /** Lonceng antrean pekerjaan; dirakit di layout supaya bilah ini tetap murni tampilan. */
  notifications?: React.ReactNode;
}) {
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
        {/* Modul penggunaan disajikan sebagai halaman berdiri sendiri di `public/`,
            bukan di dalam shell aplikasi: ia punya tata letak dan gaya cetaknya
            sendiri. Middleware tetap melindunginya seperti halaman lain. */}
        <a
          href="/modul.html"
          target="_blank"
          rel="noopener"
          className="rounded border border-base-700 px-2.5 py-1.5 font-heading text-[10px] uppercase tracking-wider text-ink-muted transition hover:border-accent/40 hover:text-accent"
        >
          Modul
        </a>
        {notifications}
        <Clock />
        <div className="flex items-center gap-2.5 border-l border-base-800 pl-5">
          <div className="text-right leading-tight">
            <div className="text-xs font-semibold text-ink">{name}</div>
            <div className="text-[10px] uppercase tracking-wider text-ink-muted">{roleName}</div>
          </div>
          <form action="/api/auth/logout" method="post">
            <button
              type="submit"
              className="rounded border border-base-700 px-2.5 py-1.5 text-[10px] uppercase tracking-wider text-ink-muted transition hover:border-accent/40 hover:text-accent"
            >
              Keluar
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
