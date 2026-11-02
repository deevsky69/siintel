import Link from "next/link";
import { LevelBadge, Stars } from "@/components/warga/bits";
import { type MapAreaDatum, PublicMap } from "@/components/warga/public-map";
import { getPublicSummary, highlightAreas, longMonth, type PublicSummary } from "@/lib/warga";
import { getImbauanPublik } from "./lapor/actions";

export const metadata = { title: "SIGAP WARGA — Polres Metro Jakarta Selatan" };
export const dynamic = "force-dynamic";

/**
 * Beranda SIGAP WARGA (2 November 2026) — peta di depan, isi lain di bawahnya.
 *
 * Yang tampil: imbauan yang sudah diterbitkan, tingkat kerawanan kasar per kecamatan, dan
 * sorotan Survey Rasa Aman. Tidak ada skor, prediksi, maupun titik kejadian: keputusan
 * pemilik proyek, "sederhana saja untuk masyarakat".
 */
export default async function BerandaWarga() {
  const [summary, imbauan] = await Promise.all([
    getPublicSummary().catch(() => null),
    getImbauanPublik().catch(() => []),
  ]);
  const data = new Map<string, MapAreaDatum>(
    (summary?.kecamatan ?? []).map((row) => [
      row.kecamatan,
      { level: row.level, total: row.total },
    ]),
  );

  return (
    <div className="space-y-5">
      <section className="warga-card overflow-hidden">
        <div className="grid gap-0 md:grid-cols-5">
          <div className="p-5 md:col-span-2 md:p-7">
            <p className="text-xs font-semibold uppercase tracking-wider text-accent-soft">
              Jakarta Selatan hari ini
            </p>
            <h1 className="mt-2 text-2xl font-bold leading-tight text-ink sm:text-3xl">
              Lihat keadaan wilayahmu, lapor, dan beri ulasan.
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              Warna peta menunjukkan tingkat kerawanan kasar dua belas bulan terakhir. Ketuk wilayah
              untuk melihat angkanya.
            </p>
            <div className="mt-5 flex flex-col gap-2 sm:flex-row md:flex-col">
              <Link href="/lapor" className="warga-btn warga-btn-primary">
                Lapor kejadian
              </Link>
              <a href="tel:110" className="warga-btn warga-btn-danger">
                Darurat · 110
              </a>
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
              <Link href="/lacak" className="font-semibold text-accent-soft">
                Lacak laporan →
              </Link>
              <Link href="/lacak?tab=kendaraan" className="font-semibold text-accent-soft">
                Cek kendaraan bekas →
              </Link>
            </div>
          </div>
          <div className="bg-base-850 p-3 md:col-span-3 md:p-5">
            {summary ? (
              <PublicMap level="kecamatan" data={data} hrefPrefix="/peta?kecamatan=" />
            ) : (
              <p className="p-6 text-center text-sm text-ink-muted">Peta belum dapat dimuat.</p>
            )}
            <Legend summary={summary} />
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="warga-card p-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-base font-bold text-ink">Imbauan berlaku</h2>
            <span className="text-xs text-ink-faint">dari Polres</span>
          </div>
          {imbauan.length === 0 ? (
            <p className="mt-3 text-sm text-ink-muted">
              Tidak ada imbauan khusus saat ini. Tetap waspada dan kunci kendaraan Anda.
            </p>
          ) : (
            <ul className="mt-3 space-y-2.5">
              {imbauan.slice(0, 3).map((row) => (
                <li key={row.code} className="rounded-2xl bg-base-850 px-4 py-3">
                  <div className="flex flex-wrap items-baseline gap-x-2 text-xs">
                    <span className="font-semibold text-risk-high">{row.threat_type}</span>
                    <span className="text-ink-muted">{row.area_text}</span>
                    {row.time_window ? (
                      <span className="text-ink-faint">{row.time_window} WIB</span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-ink">{row.message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="warga-card p-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-base font-bold text-ink">Survey Rasa Aman</h2>
            <Link href="/survey" className="text-xs font-semibold text-accent-soft">
              Beri ulasan →
            </Link>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            Ulasan warga per kelurahan, anonim, seperti ulasan tempat di peta.
          </p>
          {summary && highlightAreas(summary).length > 0 ? (
            <ul className="mt-3 divide-y divide-base-800">
              {highlightAreas(summary).map((area) => (
                <li key={area.kelurahan} className="flex items-center gap-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/survey?kelurahan=${encodeURIComponent(area.kelurahan)}`}
                      className="block truncate text-sm font-semibold text-ink"
                    >
                      {area.kelurahan}
                    </Link>
                    <span className="text-xs text-ink-faint">{area.kecamatan}</span>
                  </div>
                  <Stars value={area.rating} size="text-sm" />
                  <span className="text-xs tabular-nums text-ink-muted">({area.rating_count})</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-ink-muted">
              Belum ada ulasan yang tayang. Jadilah yang pertama menilai kelurahan Anda.
            </p>
          )}
        </div>
      </section>

      {summary ? (
        <section className="warga-card p-5">
          <h2 className="text-base font-bold text-ink">Wilayah dengan kerawanan tinggi</h2>
          <p className="mt-1 text-xs text-ink-muted">
            {longMonth(summary.window_from)} – {longMonth(summary.window_to)} · tiga jenis
            kejahatan: pencurian kendaraan, pencurian dengan pemberatan, dan dengan kekerasan.
          </p>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {summary.areas
              .filter((area) => area.level === "TINGGI")
              .sort((a, b) => b.total - a.total)
              .slice(0, 6)
              .map((area) => (
                <li key={area.kelurahan}>
                  <Link
                    href={`/peta?kecamatan=${encodeURIComponent(area.kecamatan)}&kelurahan=${encodeURIComponent(area.kelurahan)}`}
                    className="flex items-center justify-between rounded-2xl bg-base-850 px-4 py-3 transition hover:bg-base-800"
                  >
                    <span>
                      <span className="block text-sm font-semibold text-ink">{area.kelurahan}</span>
                      <span className="text-xs text-ink-faint">{area.kecamatan}</span>
                    </span>
                    <LevelBadge level={area.level} />
                  </Link>
                </li>
              ))}
          </ul>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">{summary.basis}</p>
        </section>
      ) : null}
    </div>
  );
}

function Legend({ summary }: { summary: PublicSummary | null }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-xs text-ink-muted">
      <span className="inline-flex items-center gap-1.5">
        <i className="h-2.5 w-2.5 rounded-full bg-risk-low" /> Rendah
      </span>
      <span className="inline-flex items-center gap-1.5">
        <i className="h-2.5 w-2.5 rounded-full bg-risk-moderate" /> Sedang
      </span>
      <span className="inline-flex items-center gap-1.5">
        <i className="h-2.5 w-2.5 rounded-full bg-risk-high" /> Tinggi
      </span>
      {summary ? (
        <span className="ml-auto text-ink-faint">
          {longMonth(summary.window_from)} – {longMonth(summary.window_to)}
        </span>
      ) : null}
    </div>
  );
}
