import { Panel } from "@/components/panel";

/**
 * Penyaring daftar laporan — pencarian, rentang tanggal, dan pilihan bernilai tetap.
 *
 * ## Formulir GET, bukan keadaan di peramban
 *
 * Seluruh penyaring dikirim sebagai parameter alamat lewat `<form method="get">`. Dengan
 * begitu:
 *
 * - hasil saringan **dapat dibagikan sebagai tautan** — berguna saat paparan, dan saat
 *   seseorang meminta rekan melihat hal yang sama;
 * - tombol mundur peramban bekerja seperti yang diharapkan;
 * - penyaringan dikerjakan di **query database**, bukan dengan menarik seluruh baris lalu
 *   memilahnya di peramban. Yang terakhir akan menembus batas cakupan wilayah: baris yang
 *   tidak boleh dilihat pengguna tidak boleh sampai ke peramban sama sekali;
 * - tidak ada satu baris JavaScript pun yang dibutuhkan agar penyaringnya bekerja.
 *
 * Nilai yang sedang berlaku dipasang sebagai `defaultValue`, bukan `value`, supaya pengguna
 * dapat mengetik tanpa setiap ketukan memaksa halaman dimuat ulang.
 */

export type SelectFilter = {
  name: string;
  label: string;
  /** Nilai tersimpan → label yang dibaca pengguna. */
  options: Record<string, string>;
  current: string;
  anyLabel: string;
};

export function ReportFilters({
  action,
  search,
  searchLabel,
  searchHint,
  dateFrom,
  dateTo,
  dateLabel,
  selects,
  resultCount,
  filtered,
}: {
  action: string;
  search: string;
  searchLabel: string;
  searchHint: string;
  dateFrom: string;
  dateTo: string;
  dateLabel: string;
  selects: SelectFilter[];
  resultCount: number;
  /** Benar bila setidaknya satu penyaring sedang berlaku. */
  filtered: boolean;
}) {
  return (
    <Panel
      title="Cari dan Saring"
      action={
        <span className="text-2xs text-ink-faint">
          {resultCount} baris{filtered ? " setelah disaring" : ""}
        </span>
      }
    >
      <form method="get" action={action} className="space-y-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="block xl:col-span-2">
            <span className="stat-label">{searchLabel}</span>
            <input
              type="search"
              name="cari"
              defaultValue={search}
              placeholder={searchHint}
              className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none"
            />
          </label>

          <label className="block">
            <span className="stat-label">{dateLabel} dari</span>
            <input
              type="date"
              name="dari"
              defaultValue={dateFrom}
              className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none"
            />
          </label>

          <label className="block">
            <span className="stat-label">{dateLabel} sampai</span>
            <input
              type="date"
              name="sampai"
              defaultValue={dateTo}
              className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none"
            />
          </label>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {selects.map((filter) => (
            <label key={filter.name} className="block">
              <span className="stat-label">{filter.label}</span>
              <select
                name={filter.name}
                defaultValue={filter.current}
                className="mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none"
              >
                <option value="">{filter.anyLabel}</option>
                {Object.entries(filter.options).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            className="rounded border border-accent/50 bg-accent/10 px-4 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider text-accent transition-colors hover:bg-accent/20"
          >
            Terapkan
          </button>
          {filtered ? (
            // Tautan biasa, bukan tombol reset: `reset` mengosongkan isian tetapi
            // meninggalkan alamat apa adanya, sehingga daftarnya tidak ikut berubah dan
            // pengguna mengira penyaringnya rusak.
            <a
              href={action}
              className="rounded border border-base-700 px-4 py-1.5 text-xs uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
            >
              Hapus saringan
            </a>
          ) : null}
          <span className="text-2xs leading-relaxed text-ink-faint">
            Hasil saringan tersimpan di alamat halaman — tautannya dapat dibagikan.
          </span>
        </div>
      </form>
    </Panel>
  );
}
