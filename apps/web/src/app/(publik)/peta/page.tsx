import Link from "next/link";
import { LevelBadge, MonthBars, Stars } from "@/components/warga/bits";
import { type MapAreaDatum, PublicMap } from "@/components/warga/public-map";
import { getPublicSummary, longMonth, threatLabel } from "@/lib/warga";

export const metadata = { title: "Peta Wilayah — SIGAP WARGA" };
export const dynamic = "force-dynamic";

/**
 * Peta wilayah untuk warga: kecamatan → kelurahan, angka di panel bawah/samping.
 *
 * Alamat menyimpan pilihan (`?kecamatan=&kelurahan=`) supaya dapat dibagikan dan tombol
 * kembali peramban bekerja. Isinya hanya yang diputuskan boleh terbuka: jumlah historis,
 * tingkat kasar, dan nilai rasa aman.
 */
export default async function PetaWarga({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return (Array.isArray(value) ? value[0] : value) ?? "";
  };
  const summary = await getPublicSummary().catch(() => null);
  if (!summary) {
    return (
      <p className="warga-card p-6 text-sm text-ink-muted">
        Peta belum dapat dimuat. Coba lagi sebentar.
      </p>
    );
  }
  const kecamatanNames = new Set(summary.kecamatan.map((row) => row.kecamatan));
  const kecamatan = kecamatanNames.has(one("kecamatan")) ? one("kecamatan") : "";
  const area = summary.areas.find(
    (row) => row.kelurahan === one("kelurahan") && (!kecamatan || row.kecamatan === kecamatan),
  );
  const kecRow = summary.kecamatan.find((row) => row.kecamatan === kecamatan) ?? null;

  const data = new Map<string, MapAreaDatum>(
    kecamatan
      ? summary.areas
          .filter((row) => row.kecamatan === kecamatan)
          .map((row) => [row.kelurahan, { level: row.level, total: row.total }])
      : summary.kecamatan.map((row) => [row.kecamatan, { level: row.level, total: row.total }]),
  );

  return (
    <div className="space-y-4">
      <nav aria-label="Jejak" className="flex flex-wrap items-center gap-1.5 text-sm">
        <Link href="/peta" className={kecamatan ? "text-accent-soft" : "font-semibold text-ink"}>
          Jakarta Selatan
        </Link>
        {kecamatan ? (
          <>
            <span className="text-ink-faint">›</span>
            <Link
              href={`/peta?kecamatan=${encodeURIComponent(kecamatan)}`}
              className={area ? "text-accent-soft" : "font-semibold text-ink"}
            >
              {kecamatan}
            </Link>
          </>
        ) : null}
        {area ? (
          <>
            <span className="text-ink-faint">›</span>
            <span className="font-semibold text-ink">{area.kelurahan}</span>
          </>
        ) : null}
      </nav>

      <div className="grid gap-4 lg:grid-cols-5">
        <section className="warga-card p-3 lg:col-span-3 lg:p-5">
          <PublicMap
            level={kecamatan ? "kelurahan" : "kecamatan"}
            focus={kecamatan || undefined}
            data={data}
            selected={area?.kelurahan ?? null}
            hrefPrefix={
              kecamatan
                ? `/peta?kecamatan=${encodeURIComponent(kecamatan)}&kelurahan=`
                : "/peta?kecamatan="
            }
          />
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
            {longMonth(summary.window_from)} – {longMonth(summary.window_to)} · tingkat dihitung
            dari jumlah kejadian tercatat, bukan prediksi.
          </p>
        </section>

        <aside className="lg:col-span-2">
          {area ? (
            <section className="warga-card p-5">
              <p className="text-xs text-ink-faint">
                {area.kecamatan} · Polsek {area.polsek ?? "—"}
              </p>
              <h1 className="mt-0.5 text-xl font-bold text-ink">Kelurahan {area.kelurahan}</h1>
              <div className="mt-3">
                <LevelBadge level={area.level} size="lg" />
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-base-850 px-4 py-3">
                  <dt className="text-xs text-ink-muted">Kejadian 12 bulan</dt>
                  <dd className="text-2xl font-bold tabular-nums text-ink">{area.total}</dd>
                </div>
                <div className="rounded-2xl bg-base-850 px-4 py-3">
                  <dt className="text-xs text-ink-muted">Rasa aman warga</dt>
                  <dd className="flex items-center gap-1.5">
                    <Stars value={area.rating} size="text-sm" />
                    <span className="text-xs text-ink-muted">
                      {area.rating_count > 0
                        ? `${area.rating} · ${area.rating_count} ulasan`
                        : "belum ada"}
                    </span>
                  </dd>
                </div>
              </dl>
              <ul className="mt-4 space-y-1.5">
                {Object.entries(area.by_threat).map(([threat, count]) => (
                  <li key={threat} className="flex items-center justify-between text-sm">
                    <span className="text-ink-muted">{threatLabel(threat)}</span>
                    <span className="font-semibold tabular-nums text-ink">{count}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-4">
                <MonthBars months={summary.months} values={area.by_month} />
              </div>
              <Link
                href={`/survey?kelurahan=${encodeURIComponent(area.kelurahan)}`}
                className="warga-btn warga-btn-ghost mt-4 w-full"
              >
                Lihat dan beri ulasan
              </Link>
            </section>
          ) : kecRow ? (
            <section className="warga-card p-5">
              <h1 className="text-xl font-bold text-ink">Kecamatan {kecRow.kecamatan}</h1>
              <div className="mt-2">
                <LevelBadge level={kecRow.level} size="lg" />
              </div>
              <p className="mt-3 text-sm text-ink-muted">
                {kecRow.total} kejadian tercatat di {kecRow.kelurahan} kelurahan dalam dua belas
                bulan terakhir. Ketuk kelurahan pada peta untuk rinciannya.
              </p>
              <ul className="mt-4 divide-y divide-base-800">
                {summary.areas
                  .filter((row) => row.kecamatan === kecRow.kecamatan)
                  .sort((a, b) => b.total - a.total)
                  .map((row) => (
                    <li key={row.kelurahan}>
                      <Link
                        href={`/peta?kecamatan=${encodeURIComponent(row.kecamatan)}&kelurahan=${encodeURIComponent(row.kelurahan)}`}
                        className="flex items-center justify-between py-2.5 text-sm"
                      >
                        <span className="font-medium text-ink">{row.kelurahan}</span>
                        <span className="flex items-center gap-2">
                          <span className="tabular-nums text-ink-muted">{row.total}</span>
                          <LevelBadge level={row.level} />
                        </span>
                      </Link>
                    </li>
                  ))}
              </ul>
            </section>
          ) : (
            <section className="warga-card p-5">
              <h1 className="text-xl font-bold text-ink">Pilih kecamatan</h1>
              <p className="mt-2 text-sm text-ink-muted">
                Ketuk kecamatan pada peta, atau pilih dari daftar.
              </p>
              <ul className="mt-4 divide-y divide-base-800">
                {summary.kecamatan.map((row) => (
                  <li key={row.kecamatan}>
                    <Link
                      href={`/peta?kecamatan=${encodeURIComponent(row.kecamatan)}`}
                      className="flex items-center justify-between py-2.5 text-sm"
                    >
                      <span className="font-medium text-ink">{row.kecamatan}</span>
                      <LevelBadge level={row.level} />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
