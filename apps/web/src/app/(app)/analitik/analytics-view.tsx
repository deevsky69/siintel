import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import type {
  SpatialPatternResponse,
  ThreatTypeCount,
  TimePatternResponse,
  TrendResponse,
} from "@/lib/analytics";
import {
  type AnalyticsSelection,
  analyticsHref,
  barWidth,
  decimalText,
  formatDate,
  HEAT_CLASSES,
  heatLevel,
  linePath,
  monthTicks,
  peakOfSeries,
  seriesColor,
  shareText,
  threatLabel,
  toggledThreatType,
} from "./display";

/**
 * Layar Crime Analytics — tren, jam rawan, dan perbandingan antarwilayah.
 *
 * Komponen ini **murni presentasi**: seluruh isinya datang dari tiga endpoint analitik.
 * Tidak ada angka yang dihitung, tidak ada nilai yang ditandai menonjol, dan tidak ada
 * kalimat yang menyatakan apa yang akan terjadi.
 *
 * Empat aturan tampilan yang mengikat:
 *
 * 1. **Layar menyatakan bedanya dengan Crime Pattern DNA di paling atas**, bukan di
 *    catatan kaki. Dua layar yang membaca tabel sama tetapi menjawab pertanyaan berbeda
 *    akan tertukar bila bedanya tidak disebut lebih dulu.
 * 2. **Persentase tidak pernah tampil tanpa penyebutnya**, dan sel matriks wilayah membawa
 *    dua persentase berpenyebut berbeda — keduanya dijelaskan lewat `share_basis`.
 * 3. **Skala gambar bukan pernyataan.** Panjang batang dan tingkat warna diskalakan
 *    terhadap nilai terbesar; setiap panel menyatakan skalanya, karena tidak ada ambang
 *    "rawan" yang ditetapkan siapa pun.
 * 4. **Grafik digambar dengan SVG dan div**, tanpa pustaka grafik.
 */

const CHART_WIDTH = 720;
const CHART_HEIGHT = 150;

/** Sumbu 36 bulan hanya diberi label tiap enam bulan agar tetap terbaca. */
const MONTH_TICK_EVERY = 6;

function ThreatFilter({
  available,
  selection,
}: {
  available: ThreatTypeCount[];
  selection: AnalyticsSelection;
}) {
  return (
    <nav aria-label="Jenis gangguan" className="flex flex-wrap items-center gap-2">
      <span className="stat-label w-16 shrink-0">Jenis</span>
      <Link
        href={analyticsHref(selection, { threatType: null })}
        aria-current={selection.threatType === null ? "true" : undefined}
        className={
          selection.threatType === null
            ? "rounded border border-accent/60 bg-accent/10 px-2.5 py-1 text-[11px] uppercase tracking-wider text-accent"
            : "rounded border border-base-800 px-2.5 py-1 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink"
        }
      >
        Semua
      </Link>
      {available.map((row) => (
        <Link
          key={row.threat_type}
          href={analyticsHref(selection, {
            threatType: toggledThreatType(selection.threatType, row.threat_type),
          })}
          aria-current={selection.threatType === row.threat_type ? "true" : undefined}
          className={
            selection.threatType === row.threat_type
              ? "rounded border border-accent/60 bg-accent/10 px-2.5 py-1 text-[11px] uppercase tracking-wider text-accent"
              : "rounded border border-base-800 px-2.5 py-1 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink"
          }
        >
          {threatLabel(row.threat_type)}
          <span className="ml-1.5 font-mono text-ink-faint">{row.incidents}</span>
        </Link>
      ))}
    </nav>
  );
}

/**
 * Penyaring tanggal sebagai formulir GET biasa.
 *
 * Sengaja tanpa JavaScript sisi klien: `method="get"` menaruh isian langsung di alamat,
 * sehingga halaman tetap server component dan keadaannya tetap dapat dibagikan.
 */
function RangeFilter({ selection }: { selection: AnalyticsSelection }) {
  return (
    <form method="get" action="/analitik" className="flex flex-wrap items-end gap-2">
      {selection.threatType ? (
        <input type="hidden" name="jenis" value={selection.threatType} />
      ) : null}
      <label className="flex flex-col gap-1">
        <span className="stat-label">Dari tanggal</span>
        <input
          type="date"
          name="dari"
          defaultValue={selection.dateFrom ?? ""}
          className="rounded border border-base-800 bg-base-950 px-2 py-1 text-xs text-ink"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="stat-label">Sampai tanggal</span>
        <input
          type="date"
          name="sampai"
          defaultValue={selection.dateTo ?? ""}
          className="rounded border border-base-800 bg-base-950 px-2 py-1 text-xs text-ink"
        />
      </label>
      <button
        type="submit"
        className="rounded border border-base-800 px-3 py-1.5 font-heading text-[11px] font-semibold uppercase tracking-wider text-ink hover:border-accent/60 hover:text-accent"
      >
        Terapkan
      </button>
      {selection.dateFrom || selection.dateTo ? (
        <Link
          href={analyticsHref(selection, { dateFrom: null, dateTo: null })}
          className="panel-action py-1.5"
        >
          Lepas rentang
        </Link>
      ) : null}
    </form>
  );
}

/** Grafik tren: satu garis per jenis gangguan, digambar sebagai SVG langsung. */
function TrendPanel({ trend }: { trend: TrendResponse }) {
  const peak = peakOfSeries(trend.series);
  const ticks = monthTicks(trend.months.length, MONTH_TICK_EVERY);

  return (
    <Panel
      title="Tren Bulanan"
      className="col-span-12 xl:col-span-7"
      action={
        <span className="text-[10px] uppercase tracking-wider text-ink-faint">
          {trend.months_counted} bulan · {trend.incidents} kejadian
        </span>
      }
      bodyClassName="flex flex-col gap-3"
    >
      {trend.months.length === 0 || trend.incidents === 0 ? (
        <EmptyState label="Tidak ada kejadian pada rentang ini, sehingga tidak ada tren untuk digambar." />
      ) : (
        <>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {trend.series.map((row, index) => (
              <span key={row.threat_type} className="flex items-center gap-1.5 text-[10px]">
                <span
                  className="h-1.5 w-3 rounded-full"
                  style={{ backgroundColor: seriesColor(index) }}
                />
                <span className="text-ink">{threatLabel(row.threat_type)}</span>
                <span className="font-mono text-ink-muted">
                  {shareText(row.share_percent, trend.denominator)}
                </span>
              </span>
            ))}
          </div>

          <svg
            viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT + 16}`}
            className="w-full"
            role="img"
            aria-label={`Tren kejadian per bulan menurut jenis gangguan, ${trend.months.length} bulan`}
          >
            <title>Kejadian per bulan menurut jenis gangguan</title>
            {trend.series.map((row, index) => (
              <path
                key={row.threat_type}
                d={linePath(row.monthly, peak, CHART_WIDTH, CHART_HEIGHT)}
                fill="none"
                stroke={seriesColor(index)}
                strokeWidth={1.6}
                strokeLinejoin="round"
              />
            ))}
            {ticks.map((index) => (
              <text
                key={trend.months[index].key}
                x={(index / Math.max(trend.months.length - 1, 1)) * CHART_WIDTH}
                y={CHART_HEIGHT + 12}
                textAnchor={
                  index === 0 ? "start" : index === trend.months.length - 1 ? "end" : "middle"
                }
                className="fill-ink-muted"
                style={{ fontSize: 9 }}
              >
                {trend.months[index].label}
              </text>
            ))}
          </svg>

          <p className="text-[10px] leading-relaxed text-ink-faint">
            Tinggi garis relatif terhadap bulan terbanyak satu jenis ({peak} kejadian), bukan
            terhadap total. Rata-rata seluruh jenis {decimalText(trend.mean_per_month)} kejadian per
            bulan.
          </p>

          <details>
            <summary className="cursor-pointer text-[10px] uppercase tracking-wider text-ink-muted hover:text-accent">
              Angka per bulan
            </summary>
            <ul className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-3">
              {trend.months.map((month) => (
                <li
                  key={month.key}
                  className="flex justify-between gap-2 text-[10px] text-ink-muted"
                >
                  <span>{month.label}</span>
                  <span className="font-mono text-ink">
                    {month.incidents} · {shareText(month.share_percent, trend.denominator)}
                  </span>
                </li>
              ))}
            </ul>
          </details>

          <p className="text-[10px] leading-relaxed text-ink-faint">{trend.mean_basis}</p>
          <p className="text-[10px] leading-relaxed text-ink-faint">{trend.peak_basis}</p>
        </>
      )}
    </Panel>
  );
}

/** Ringkasan komposisi jenis pada rentang yang sedang dilihat. */
function CompositionPanel({ trend }: { trend: TrendResponse }) {
  const peak = trend.series.reduce((highest, row) => Math.max(highest, row.incidents), 0);

  return (
    <Panel
      title="Distribusi Jenis"
      className="col-span-12 xl:col-span-5"
      action={
        <Link href="/pola" className="panel-action">
          Profil per jenis →
        </Link>
      }
      bodyClassName="flex flex-col gap-3"
    >
      {trend.series.length === 0 ? (
        <EmptyState label="Tidak ada jenis gangguan yang tercatat pada rentang ini." />
      ) : (
        <>
          <ul className="flex flex-col gap-1.5">
            {trend.series.map((row, index) => (
              <li key={row.threat_type} className="flex items-center gap-2.5">
                <span className="w-28 shrink-0 truncate text-xs text-ink" title={row.threat_type}>
                  {threatLabel(row.threat_type)}
                </span>
                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-base-800">
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${barWidth(row.incidents, peak)}%`,
                      backgroundColor: seriesColor(index),
                    }}
                  />
                </span>
                <span className="w-10 text-right font-mono text-xs font-semibold text-ink">
                  {row.incidents}
                </span>
                <span className="w-36 shrink-0 text-right text-[10px] text-ink-muted">
                  {shareText(row.share_percent, trend.denominator)}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-[10px] leading-relaxed text-ink-faint">
            Panjang batang relatif terhadap jenis terbanyak ({peak} kejadian), bukan terhadap 100%.
            Jumlah dan persentase tercantum pada tiap batang.
          </p>
        </>
      )}
    </Panel>
  );
}

/** Matriks hari x jam: 168 sel, digambar sebagai kotak berkelas warna tetap. */
function TimePatternPanel({ pattern }: { pattern: TimePatternResponse }) {
  const peak = pattern.peak_cell?.incidents ?? 0;

  return (
    <Panel
      title="Hari & Jam Rawan"
      className="col-span-12"
      action={
        <span className="text-[10px] uppercase tracking-wider text-ink-faint">
          {pattern.cells} sel · {pattern.incidents} kejadian
        </span>
      }
      bodyClassName="flex flex-col gap-3"
    >
      {pattern.incidents === 0 ? (
        <EmptyState label="Tidak ada kejadian pada rentang ini, sehingga matriks hari × jam kosong." />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-separate border-spacing-0.5 text-left">
              <caption className="sr-only">
                Jumlah kejadian menurut hari dalam pekan dan jam kejadian
              </caption>
              <thead>
                <tr>
                  <th className="stat-label w-14 font-medium">Hari</th>
                  {pattern.hours.map((hour) => (
                    <th
                      key={hour.hour}
                      scope="col"
                      className="text-center text-[9px] font-normal text-ink-faint"
                    >
                      {hour.hour % 3 === 0 ? String(hour.hour).padStart(2, "0") : ""}
                    </th>
                  ))}
                  <th className="stat-label w-12 text-right font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {pattern.days.map((day) => (
                  <tr key={day.day}>
                    <th scope="row" className="pr-1 text-[11px] font-normal text-ink-muted">
                      {day.label}
                    </th>
                    {day.cells.map((cell) => (
                      <td key={cell.hour} className="p-0">
                        <div
                          className={`h-4 rounded-sm ${HEAT_CLASSES[heatLevel(cell.incidents, peak)]}`}
                          title={`${day.label} ${cell.label} — ${cell.incidents} kejadian, ${shareText(cell.share_percent, pattern.denominator)}`}
                        />
                      </td>
                    ))}
                    <td className="pl-1 text-right font-mono text-[11px] text-ink">
                      {day.incidents}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1 text-[10px] text-ink-faint">
              <span className="stat-label">Skala</span>
              {HEAT_CLASSES.map((className, index) => (
                <span key={className} className={`h-3 w-4 rounded-sm ${className}`}>
                  <span className="sr-only">tingkat {index}</span>
                </span>
              ))}
              <span className="ml-1">
                0 sampai {peak} kejadian per sel — relatif terhadap sel terbanyak, bukan terhadap
                ambang.
              </span>
            </span>
          </div>

          {pattern.peak_cell ? (
            <p className="text-[11px] leading-relaxed text-ink-muted">
              Sel terbanyak: <span className="text-ink">{pattern.peak_cell.label}</span> dengan{" "}
              {pattern.peak_cell.incidents} kejadian (
              {shareText(pattern.peak_cell.share_percent, pattern.denominator)}).
            </p>
          ) : null}

          <details>
            <summary className="cursor-pointer text-[10px] uppercase tracking-wider text-ink-muted hover:text-accent">
              Angka per jam, seluruh hari
            </summary>
            <ul className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-4">
              {pattern.hours.map((hour) => (
                <li
                  key={hour.hour}
                  className="flex justify-between gap-2 text-[10px] text-ink-muted"
                >
                  <span>{hour.label}</span>
                  <span className="font-mono text-ink">
                    {hour.incidents} · {shareText(hour.share_percent, pattern.denominator)}
                  </span>
                </li>
              ))}
            </ul>
          </details>

          <p className="text-[10px] leading-relaxed text-ink-faint">{pattern.cell_basis}</p>
          <p className="text-[10px] leading-relaxed text-ink-faint">{pattern.time_basis}</p>
        </>
      )}
    </Panel>
  );
}

/** Perbandingan antarwilayah: satu baris per kecamatan, tersusun menurut jenis. */
function SpatialPanel({ spatial }: { spatial: SpatialPatternResponse }) {
  const columns = spatial.threat_types.map((row) => row.threat_type);

  return (
    <Panel
      title="Perbandingan Antarwilayah"
      className="col-span-12"
      action={
        <span className="text-[10px] uppercase tracking-wider text-ink-faint">
          {spatial.areas_compared} kecamatan · {spatial.incidents} kejadian
        </span>
      }
      bodyClassName="flex flex-col gap-3"
    >
      {spatial.areas.length === 0 ? (
        <EmptyState label="Tidak ada kejadian pada rentang ini, sehingga tidak ada wilayah untuk dibandingkan." />
      ) : (
        <>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {spatial.threat_types.map((row, index) => (
              <span key={row.threat_type} className="flex items-center gap-1.5 text-[10px]">
                <span
                  className="h-1.5 w-3 rounded-full"
                  style={{ backgroundColor: seriesColor(index) }}
                />
                <span className="text-ink">{threatLabel(row.threat_type)}</span>
                <span className="font-mono text-ink-muted">{row.incidents}</span>
              </span>
            ))}
          </div>

          <ul className="flex flex-col gap-2">
            {spatial.areas.map((area) => (
              <li key={area.kecamatan}>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs text-ink">
                    {area.kecamatan}
                    {area.polsek ? (
                      <span className="ml-1.5 text-[10px] text-ink-faint">{area.polsek}</span>
                    ) : null}
                  </span>
                  <span className="shrink-0 text-[10px] text-ink-muted">
                    {area.incidents} kejadian · {shareText(area.share_percent, spatial.denominator)}
                  </span>
                </div>
                {/* Batang tersusun: lebar tiap ruas = bagian jenis itu terhadap kejadian
                    kecamatannya sendiri, sehingga seluruh baris selalu penuh 100%. */}
                <div className="mt-1 flex h-2 overflow-hidden rounded-full bg-base-800">
                  {area.by_threat.map((cell, index) => (
                    <span
                      key={cell.threat_type}
                      className="block h-full"
                      style={{
                        width: `${cell.share_of_area_percent}%`,
                        backgroundColor: seriesColor(index),
                      }}
                      title={`${threatLabel(cell.threat_type)} — ${cell.incidents} kejadian, ${shareText(cell.share_of_area_percent, area.denominator)} di ${area.kecamatan}`}
                    />
                  ))}
                </div>
              </li>
            ))}
          </ul>

          <details>
            <summary className="cursor-pointer text-[10px] uppercase tracking-wider text-ink-muted hover:text-accent">
              Tabel wilayah × jenis
            </summary>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-base-800">
                    <th className="stat-label pb-2 font-medium">Kecamatan</th>
                    {columns.map((name) => (
                      <th key={name} className="stat-label pb-2 text-right font-medium">
                        {threatLabel(name)}
                      </th>
                    ))}
                    <th className="stat-label pb-2 text-right font-medium">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {spatial.areas.map((area) => (
                    <tr key={area.kecamatan} className="border-b border-base-800/60">
                      <td className="py-1.5 pr-3 text-ink">{area.kecamatan}</td>
                      {area.by_threat.map((cell) => (
                        <td
                          key={cell.threat_type}
                          className="py-1.5 text-right font-mono text-ink-muted"
                          title={`${cell.share_of_area_percent}% dari ${area.denominator} kejadian ${area.kecamatan}; ${cell.share_of_threat_percent}% dari seluruh kejadian jenis ini`}
                        >
                          {cell.incidents}
                        </td>
                      ))}
                      <td className="py-1.5 text-right font-mono font-semibold text-ink">
                        {area.incidents}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td className="py-1.5 pr-3 text-ink-muted">Seluruh cakupan</td>
                    {spatial.threat_types.map((row) => (
                      <td
                        key={row.threat_type}
                        className="py-1.5 text-right font-mono text-ink-muted"
                      >
                        {row.incidents}
                      </td>
                    ))}
                    <td className="py-1.5 text-right font-mono font-semibold text-ink">
                      {spatial.incidents}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </details>

          <p className="text-[10px] leading-relaxed text-ink-faint">{spatial.share_basis}</p>
          <p className="text-[10px] leading-relaxed text-ink-faint">{spatial.comparison_basis}</p>
          <p className="rounded border border-base-800 bg-base-950/60 p-2.5 text-[11px] leading-relaxed text-ink-muted">
            {spatial.rate_basis}
          </p>
        </>
      )}
    </Panel>
  );
}

export function AnalyticsView({
  selection,
  trend,
  pattern,
  spatial,
}: {
  selection: AnalyticsSelection;
  trend: TrendResponse;
  pattern: TimePatternResponse;
  spatial: SpatialPatternResponse;
}) {
  return (
    <div className="grid grid-cols-12 gap-3">
      <Panel
        title="Crime Analytics"
        className="col-span-12"
        action={
          <span className="text-[10px] uppercase tracking-wider text-ink-faint">
            {trend.source.incidents} kejadian · {formatDate(trend.source.date_from)} –{" "}
            {formatDate(trend.source.date_to)}
          </span>
        }
        bodyClassName="flex flex-col gap-3"
      >
        {trend.threat_types.length === 0 ? (
          <EmptyState label="Tidak ada kejadian yang dapat ditampilkan untuk kewenangan Anda." />
        ) : (
          <ThreatFilter available={trend.threat_types} selection={selection} />
        )}
        <RangeFilter selection={selection} />

        {/* Bedanya dengan /pola dinyatakan di atas, bukan di kaki halaman: dua layar yang
            membaca tabel sama akan tertukar bila bedanya tidak terbaca lebih dulu. */}
        <p className="rounded border border-base-800 bg-base-950/60 p-2.5 text-[11px] leading-relaxed text-ink-muted">
          {trend.related_analysis_basis}{" "}
          <Link href="/pola" className="text-accent hover:text-accent-soft">
            Buka Crime Pattern DNA →
          </Link>
        </p>
        <p className="text-[10px] leading-relaxed text-ink-faint">{trend.analysis_basis}</p>
        <p className="text-[10px] leading-relaxed text-ink-faint">{trend.scope_basis}</p>
        {selection.threatType ? (
          <p className="text-[10px] leading-relaxed text-ink-faint">
            Penyaring jenis <span className="text-ink">{threatLabel(selection.threatType)}</span>{" "}
            berlaku untuk tren dan matriks hari × jam. Perbandingan antarwilayah tetap menampilkan
            seluruh jenis, karena justru jenis itulah kolom perbandingannya.
          </p>
        ) : null}
      </Panel>

      <TrendPanel trend={trend} />
      <CompositionPanel trend={trend} />
      <TimePatternPanel pattern={pattern} />
      <SpatialPanel spatial={spatial} />
    </div>
  );
}
