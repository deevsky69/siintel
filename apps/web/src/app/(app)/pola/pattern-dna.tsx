import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import type {
  PatternDistribution,
  PatternProfile,
  RepeatProfile,
  ThreatTypeCount,
} from "@/lib/patterns";
import { barWidth, formatDate, humanize, patternHref, peakOf, shareText, threatLabel } from "./dna";

/**
 * Layar Crime Pattern DNA — lima dimensi satu jenis gangguan, berdampingan.
 *
 * Komponen ini **murni presentasi**: seluruh isinya datang dari `GET /analytics/crime-pattern-dna`.
 * Tidak ada angka yang dihitung, tidak ada nilai yang ditandai menonjol, dan tidak ada
 * kalimat yang menyatakan apa yang akan terjadi. Yang tampil adalah sebaran kejadian yang
 * sudah terjadi (CLAUDE.md §27) — dan layar menyatakannya di paling atas, bukan dalam
 * catatan kaki, karena "DNA" mudah sekali dibaca sebagai ramalan.
 *
 * Tiga aturan tampilan yang mengikat:
 *
 * 1. **Persentase tidak pernah tampil sendirian.** Setiap batang membawa jumlah kejadian
 *    dan penyebutnya ("24,6% dari 464 kejadian").
 * 2. **Panjang batang bukan persentase.** Batang diskalakan terhadap golongan terbesar
 *    agar sebaran jam terbaca; skala itu dinyatakan di setiap panel.
 * 3. **Urutan tidak diubah di layar.** `ordering` dari backend dihormati: kategori urut
 *    terbanyak, waktu urut jam/hari.
 */

/** Nama dimensi pada docs/01 §5.4, ditampilkan bersama padanan Indonesianya. */
function DimensionPanel({
  code,
  name,
  children,
  className,
}: {
  code: string;
  name: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Panel title={`${code} · ${name}`} className={className} bodyClassName="flex flex-col gap-4">
      {children}
    </Panel>
  );
}

function ScaleNote({ peak, label }: { peak: number; label: string }) {
  return (
    <p className="text-[10px] leading-relaxed text-ink-faint">
      Panjang batang relatif terhadap {label} terbanyak ({peak} kejadian), bukan terhadap 100%.
      Jumlah dan persentase tercantum pada tiap batang.
    </p>
  );
}

/** Sebaran kategori: satu baris per golongan, urut terbanyak sesuai `ordering: rank`. */
function RankedDistribution({ distribution }: { distribution: PatternDistribution }) {
  const peak = peakOf(distribution);

  if (distribution.buckets.length === 0) {
    return (
      <div>
        <h3 className="stat-label mb-2">{distribution.label}</h3>
        <EmptyState label="Tidak ada nilai yang tercatat untuk dimensi ini." />
      </div>
    );
  }

  return (
    <div>
      <h3 className="stat-label mb-2">{distribution.label}</h3>
      <ul className="flex flex-col gap-1.5">
        {distribution.buckets.map((bucket) => (
          <li key={bucket.key} className="flex items-center gap-2.5">
            <span className="w-28 shrink-0 truncate text-xs text-ink" title={bucket.label}>
              {humanize(bucket.label)}
            </span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-base-800">
              <span
                className="block h-full rounded-full bg-accent-deep"
                style={{ width: `${barWidth(bucket.incidents, peak)}%` }}
              />
            </span>
            <span className="w-10 text-right font-mono text-xs font-semibold text-ink">
              {bucket.incidents}
            </span>
            <span className="w-36 shrink-0 text-right text-[10px] text-ink-muted">
              {shareText(bucket.share_percent, distribution.denominator)}
            </span>
          </li>
        ))}
      </ul>
      <ScaleNote peak={peak} label="golongan" />
    </div>
  );
}

/**
 * Sebaran waktu: kolom berurut jam/hari, termasuk yang bernilai nol.
 *
 * Digambar dengan div bertinggi relatif, bukan pustaka grafik — satu grafik batang
 * sederhana tidak sepadan dengan menambah dependensi (lihat `components/dashboard/trend-chart.tsx`).
 */
function NaturalDistribution({ distribution }: { distribution: PatternDistribution }) {
  const peak = peakOf(distribution);
  const compact = distribution.buckets.length > 12;

  return (
    <div>
      <h3 className="stat-label mb-2">{distribution.label}</h3>
      <ul className="flex h-24 items-end gap-1">
        {distribution.buckets.map((bucket) => (
          <li
            key={bucket.key}
            className="flex h-full flex-1 flex-col justify-end"
            title={`${bucket.label} — ${bucket.incidents} kejadian, ${shareText(bucket.share_percent, distribution.denominator)}`}
          >
            <span
              className="block w-full rounded-t bg-accent-deep"
              style={{
                height: `${Math.max(barWidth(bucket.incidents, peak), bucket.incidents > 0 ? 2 : 0)}%`,
              }}
            />
          </li>
        ))}
      </ul>
      <ul className="mt-1 flex gap-1" aria-hidden="true">
        {distribution.buckets.map((bucket, index) => (
          <li
            key={bucket.key}
            className="flex-1 text-center text-[9px] leading-tight text-ink-faint"
          >
            {/* Sebaran 24 jam hanya diberi label tiap tiga jam agar tetap terbaca. */}
            {compact && index % 3 !== 0 ? "" : bucket.label}
          </li>
        ))}
      </ul>
      {/* Daftar angka lengkap untuk pembaca layar dan untuk pembacaan teliti. */}
      <details className="mt-2">
        <summary className="cursor-pointer text-[10px] uppercase tracking-wider text-ink-muted hover:text-accent">
          Angka {distribution.label.toLocaleLowerCase("id-ID")}
        </summary>
        <ul className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-3">
          {distribution.buckets.map((bucket) => (
            <li key={bucket.key} className="flex justify-between gap-2 text-[10px] text-ink-muted">
              <span>{bucket.label}</span>
              <span className="font-mono text-ink">
                {bucket.incidents} · {shareText(bucket.share_percent, distribution.denominator)}
              </span>
            </li>
          ))}
        </ul>
      </details>
      <ScaleNote peak={peak} label="jam/hari" />
    </div>
  );
}

function Distribution({ distribution }: { distribution: PatternDistribution }) {
  return distribution.ordering === "natural" ? (
    <NaturalDistribution distribution={distribution} />
  ) : (
    <RankedDistribution distribution={distribution} />
  );
}

/** Dimensi REPEAT: grid yang berulang, berapa kali, dan sepanjang rentang tanggal berapa. */
function RepeatPanel({ repeat }: { repeat: RepeatProfile }) {
  return (
    <DimensionPanel code="REPEAT" name="Pengulangan" className="col-span-12 xl:col-span-6">
      <dl className="grid grid-cols-3 gap-3">
        <div>
          <dt className="stat-label">Grid berulang</dt>
          <dd className="stat-value">{repeat.repeat_grids}</dd>
        </div>
        <div>
          <dt className="stat-label">Grid berkejadian</dt>
          <dd className="stat-value">{repeat.grids_with_incidents}</dd>
        </div>
        <div>
          <dt className="stat-label">Grid sekali saja</dt>
          <dd className="stat-value">{repeat.single_incident_grids}</dd>
        </div>
      </dl>

      {repeat.grids.length === 0 ? (
        <EmptyState label="Tidak ada grid yang mengalami kejadian berulang untuk jenis ini." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-base-800">
                <th className="stat-label py-1.5 font-medium">Grid</th>
                <th className="stat-label py-1.5 font-medium">Kecamatan</th>
                <th className="stat-label py-1.5 text-right font-medium">Kejadian</th>
                <th className="stat-label py-1.5 text-right font-medium">Bagian</th>
                <th className="stat-label py-1.5 font-medium">Rentang</th>
              </tr>
            </thead>
            <tbody>
              {repeat.grids.map((grid) => (
                <tr key={grid.grid_id} className="border-b border-base-800/60">
                  <td className="py-1.5 font-mono text-ink">{grid.grid_id}</td>
                  <td className="py-1.5 text-ink-muted">{grid.kecamatan}</td>
                  <td className="py-1.5 text-right font-mono font-semibold text-ink">
                    {grid.incidents}
                  </td>
                  <td className="py-1.5 text-right text-[10px] text-ink-muted">
                    {shareText(grid.share_percent, repeat.denominator)}
                  </td>
                  <td className="py-1.5 text-[10px] text-ink-muted">
                    {formatDate(grid.first_date)} – {formatDate(grid.last_date)}
                    <span className="text-ink-faint"> ({grid.span_days} hari)</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[10px] leading-relaxed text-ink-faint">{repeat.basis}</p>
    </DimensionPanel>
  );
}

export function PatternDna({
  available,
  selected,
  profile,
  scopeBasis,
  analysisBasis,
  source,
}: {
  available: ThreatTypeCount[];
  selected: string | null;
  profile: PatternProfile | null;
  scopeBasis: string;
  analysisBasis: string;
  source: { date_from: string | null; date_to: string | null; incidents: number };
}) {
  return (
    <div className="grid grid-cols-12 gap-3">
      <Panel
        title="Crime Pattern DNA"
        className="col-span-12"
        action={
          <span className="text-[10px] uppercase tracking-wider text-ink-faint">
            {source.incidents} kejadian · {formatDate(source.date_from)} –{" "}
            {formatDate(source.date_to)}
          </span>
        }
        bodyClassName="flex flex-col gap-3"
      >
        {available.length === 0 ? (
          <EmptyState label="Tidak ada kejadian yang dapat ditampilkan untuk kewenangan Anda." />
        ) : (
          <nav aria-label="Jenis gangguan" className="flex flex-wrap items-center gap-2">
            {available.map((row) => (
              <Link
                key={row.threat_type}
                href={patternHref(row.threat_type)}
                scroll={false}
                aria-current={selected === row.threat_type ? "true" : undefined}
                className={
                  selected === row.threat_type
                    ? "rounded border border-accent/60 bg-accent/10 px-2.5 py-1 text-[11px] uppercase tracking-wider text-accent"
                    : "rounded border border-base-800 px-2.5 py-1 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink"
                }
              >
                {threatLabel(row.threat_type)}
                <span className="ml-1.5 font-mono text-ink-faint">{row.incidents}</span>
              </Link>
            ))}
          </nav>
        )}

        {/* Pernyataan ini berada di atas, bukan di kaki halaman: "DNA" terlalu mudah
            dibaca sebagai ramalan, dan koreksinya harus terbaca lebih dulu. */}
        <p className="rounded border border-base-800 bg-base-950/60 p-2.5 text-[11px] leading-relaxed text-ink-muted">
          {analysisBasis}
        </p>
        <p className="text-[10px] leading-relaxed text-ink-faint">{scopeBasis}</p>
        {profile ? (
          <p className="text-[10px] leading-relaxed text-ink-faint">{profile.sample_note}</p>
        ) : null}
      </Panel>

      {profile === null || profile.incidents === 0 ? (
        <Panel title="Profil Pola" className="col-span-12">
          <EmptyState label="Belum ada kejadian yang dapat diprofilkan untuk pilihan ini." />
        </Panel>
      ) : (
        <>
          <DimensionPanel code="WHERE" name="Di mana" className="col-span-12 xl:col-span-6">
            {profile.where.map((distribution) => (
              <Distribution key={distribution.id} distribution={distribution} />
            ))}
          </DimensionPanel>

          <DimensionPanel code="WHEN" name="Kapan" className="col-span-12 xl:col-span-6">
            {profile.when.map((distribution) => (
              <Distribution key={distribution.id} distribution={distribution} />
            ))}
            <p className="text-[10px] leading-relaxed text-ink-faint">{profile.time_basis}</p>
          </DimensionPanel>

          <DimensionPanel code="HOW" name="Modus" className="col-span-12 xl:col-span-3">
            {profile.how.map((distribution) => (
              <Distribution key={distribution.id} distribution={distribution} />
            ))}
          </DimensionPanel>

          <DimensionPanel code="TARGET" name="Sasaran" className="col-span-12 xl:col-span-3">
            {profile.target.map((distribution) => (
              <Distribution key={distribution.id} distribution={distribution} />
            ))}
          </DimensionPanel>

          <RepeatPanel repeat={profile.repeat} />
        </>
      )}
    </div>
  );
}
