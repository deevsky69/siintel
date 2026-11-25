import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ApiError } from "@/lib/api";
import { getPoldaRecap, type PoldaRecap, type RecapUnit } from "@/lib/polda";
import { poldaHref, UNIT_AREA } from "@/lib/polda-area";
import { OFF_FRAME_AREAS, polygonPoints, shapesAt, viewBoxOf } from "@/lib/wilayah";

export const dynamic = "force-dynamic";

const BULAN = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
  "Oktober", "November", "Desember",
]; // biome-ignore format: daftar bulan lebih terbaca sebaris

const angka = (value: number | null | undefined) =>
  value === null || value === undefined ? "—" : value.toLocaleString("id-ID");
const persen = (value: number | null | undefined, digits = 1) =>
  value === null || value === undefined
    ? "—"
    : `${value.toLocaleString("id-ID", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
const perubahan = (value: number | null) =>
  value === null ? "—" : `${value > 0 ? "+" : ""}${persen(value)}`;
const tanggal = (iso: string, withTime = false) =>
  new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta",
    dateStyle: "long",
    ...(withTime ? { timeStyle: "short" } : {}),
  }).format(new Date(iso));

type Ready = Extract<PoldaRecap, { available: true }>;

/**
 * Rekap kriminalitas Polda Metro Jaya per Polres (catatan 196).
 *
 * Datanya agregat dari Pusiknas — jumlah laporan dan penyelesaian per satuan per tahun —
 * sehingga layar ini hanya membandingkan satuan; ia tidak menurunkan apa pun ke kelurahan
 * dan tidak dipakai model. Polres Metro Jakarta Selatan disorot karena aplikasi ini miliknya.
 */
export default async function PoldaPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = (await searchParams).polres;
  const wanted = (Array.isArray(raw) ? raw[0] : raw) ?? null;
  let recap: PoldaRecap;
  try {
    recap = await getPoldaRecap();
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) return <TidakBerwenang />;
    throw error;
  }
  if (!recap.available) {
    return (
      <Panel title="Polda Metro Jaya">
        <EmptyState label="Rekap per Polres belum dimasukkan. Administrator memasukkannya dengan scripts/import/rekap_polda.py." />
      </Panel>
    );
  }
  const years = recap.years.map(String);
  const current = String(recap.current_year);
  const polres = recap.units.filter((unit) => unit.kind === "POLRES");
  const satker = recap.units.filter((unit) => unit.kind === "SATKER");
  const home = recap.units.find((unit) => unit.home) ?? null;
  // Satuan yang rinciannya dibuka — dari klik pada peta (halaman ini, Beranda, atau Peta)
  // atau pada nama di tabel. Nama yang tidak dikenal diabaikan, bukan galat.
  const chosen = recap.units.find((unit) => unit.name === wanted) ?? null;
  const label = (year: string) => (year === current ? `${year}*` : year);

  return (
    <div className="space-y-3">
      <Panel
        title="Polda Metro Jaya · rekap per Polres"
        action={
          <span className="text-2xs uppercase tracking-wider text-ink-faint">
            Posisi data {tanggal(recap.position_at, true)} WIB
          </span>
        }
        bodyClassName="flex flex-col gap-3"
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {years.map((year) => (
            <div key={year} className="rounded border border-base-800 bg-base-850 p-3">
              <div className="stat-label">{label(year)}</div>
              <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
                <div>
                  <dt className="text-2xs text-ink-faint">Kriminal keseluruhan (CT)</dt>
                  <dd className="tabular-nums text-base font-semibold text-ink">
                    {angka(recap.totals.overall[year]?.ct)}
                  </dd>
                  <dd className="text-2xs text-ink-muted">
                    selesai {angka(recap.totals.overall[year]?.cc)} · CR{" "}
                    {persen(recap.totals.overall[year]?.cr)}
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-faint">3C (CT)</dt>
                  <dd className="tabular-nums text-base font-semibold text-ink">
                    {angka(recap.totals.c3[year]?.ct)}
                  </dd>
                  <dd className="text-2xs text-ink-muted">
                    selesai {angka(recap.totals.c3[year]?.cc)} · CR{" "}
                    {persen(recap.totals.c3[year]?.cr)} ·{" "}
                    {persen(recap.totals.c3[year]?.of_overall_pct)} dari keseluruhan
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
        {home ? (
          <p className="rounded border border-accent/40 bg-accent/5 px-3 py-2 text-xs leading-relaxed text-ink">
            <span className="font-semibold">{home.name}</span> pada {label(current)}: 3C{" "}
            {angka(home.c3[current]?.ct)} laporan ({persen(home.c3[current]?.share_pct)} dari 3C
            Polda), peringkat {home.rank_c3} dari {recap.polres_count} Polres; kriminal keseluruhan{" "}
            {angka(home.overall[current]?.ct)} laporan, peringkat {home.rank_overall}.
          </p>
        ) : null}
        <p className="text-2xs leading-relaxed text-ink-faint">
          *) {recap.current_year} sampai {tanggal(recap.current_until)}; belum setahun penuh. Kolom
          Perubahan pada tabel = periode setara {recap.current_year} terhadap tahun sebelumnya.{" "}
          {recap.equal_period
            ? `Periode setara (${recap.equal_period.label}): 3C ${years
                .map((year) => `${year} ${angka(recap.equal_period?.c3[year]?.ct)}`)
                .join(", ")}; keseluruhan ${years
                .map((year) => `${year} ${angka(recap.equal_period?.overall[year]?.ct)}`)
                .join(", ")}.`
            : ""}
        </p>
      </Panel>

      {chosen ? <RincianSatuan unit={chosen} recap={recap} years={years} label={label} /> : null}

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,3fr)_minmax(0,9fr)]">
        <Panel title={`Peta 3C per Polres · ${label(current)}`}>
          <PetaPolres units={polres} year={current} chosen={chosen?.name ?? null} />
        </Panel>
        <Panel title="3C per Polres" bodyClassName="p-0">
          <TabelSatuan units={polres} years={years} scope="c3" label={label} />
        </Panel>
      </div>

      <Panel title="Kriminal keseluruhan per Polres" bodyClassName="p-0">
        <TabelSatuan units={polres} years={years} scope="overall" label={label} />
      </Panel>

      <Panel title="Jenis 3C per Polres" bodyClassName="p-0">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Polres</th>
                {years.map((year) => (
                  <th key={year} colSpan={3} className="text-center">
                    {label(year)}
                  </th>
                ))}
              </tr>
              <tr>
                <th />
                {years.flatMap((year) =>
                  ["Curat", "Curas", "Curanmor"].map((kind) => (
                    <th key={`${year}-${kind}`} className="text-right">
                      {kind}
                    </th>
                  )),
                )}
              </tr>
            </thead>
            <tbody>
              {polres.map((unit) => (
                <tr key={unit.name} className={unit.home ? "bg-accent/5" : ""}>
                  <td className="whitespace-nowrap font-semibold text-ink">
                    <Link href={poldaHref(unit.name)} scroll={false} className="hover:text-accent">
                      {unit.name}
                    </Link>
                  </td>
                  {years.flatMap((year) =>
                    (["curat", "curas", "curanmor"] as const).map((kind) => (
                      <td key={`${year}-${kind}`} className="text-right tabular-nums">
                        {angka(unit.c3[year]?.[kind])}
                      </td>
                    )),
                  )}
                </tr>
              ))}
              <tr className="font-semibold">
                <td>Seluruh Polda (termasuk satuan kerja)</td>
                {years.flatMap((year) =>
                  (["curat", "curas", "curanmor"] as const).map((kind) => (
                    <td key={`${year}-${kind}`} className="text-right tabular-nums">
                      {angka(recap.totals.c3[year]?.[kind])}
                    </td>
                  )),
                )}
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Panel title="Satuan kerja tingkat Polda" bodyClassName="p-0">
          <TabelSatuan units={satker} years={years} scope="overall" label={label} compact />
        </Panel>
        <Panel title="Laporan per bulan (CT)" bodyClassName="p-0">
          <TabelBulan recap={recap} years={years} label={label} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Panel title={`Jenis kejahatan terbanyak · ${label(current)}`} bodyClassName="p-0">
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="text-right">No</th>
                  <th>Jenis</th>
                  <th className="text-right">CT</th>
                </tr>
              </thead>
              <tbody>
                {(recap.top_types[current] ?? []).map((row) => (
                  <tr key={row.rank}>
                    <td className="text-right tabular-nums">{row.rank}</td>
                    <td>{row.name}</td>
                    <td className="text-right tabular-nums">{angka(row.ct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Bentuk penyelesaian 3C (CC)" bodyClassName="p-0">
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bentuk penyelesaian</th>
                  {years.map((year) => (
                    <th key={year} className="text-right">
                      {label(year)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recap.settlements.map((row) => (
                  <tr key={row.form}>
                    <td>{row.form}</td>
                    {years.map((year) => (
                      <td key={year} className="text-right tabular-nums">
                        {angka(row.counts[year])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <Panel title="Dasar angka">
        <p className="text-xs leading-relaxed text-ink-muted">{recap.basis}</p>
        <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
          Sumber: {recap.source}. Dimasukkan {tanggal(recap.imported_at, true)} WIB
          {recap.imported_by ? ` oleh ${recap.imported_by}` : ""}
          {recap.source_sha256 ? ` · SHA-256 ${recap.source_sha256.slice(0, 16)}…` : ""}. Rekap ini
          berlabel rahasia pada sumbernya: hanya untuk akun yang analitiknya mencakup seluruh
          wilayah, dan tidak ditampilkan pada layanan warga.
        </p>
      </Panel>
    </div>
  );
}

function TabelSatuan({
  units,
  years,
  scope,
  label,
  compact = false,
}: {
  units: RecapUnit[];
  years: string[];
  scope: "c3" | "overall";
  label: (year: string) => string;
  compact?: boolean;
}) {
  if (units.length === 0) return <EmptyState />;
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Satuan</th>
            {years.map((year) => (
              <th key={year} colSpan={compact ? 2 : 3} className="text-center">
                {label(year)}
              </th>
            ))}
            {compact ? null : (
              <th
                className="text-right"
                title="Perubahan periode setara tahun berjalan terhadap tahun sebelumnya"
              >
                Perubahan
              </th>
            )}
          </tr>
          <tr>
            <th />
            {years.flatMap((year) =>
              (compact ? ["CT", "CR"] : ["CT", "CC", "CR"]).map((head) => (
                <th key={`${year}-${head}`} className="text-right">
                  {head}
                </th>
              )),
            )}
            {compact ? null : <th />}
          </tr>
        </thead>
        <tbody>
          {units.map((unit) => {
            const change = scope === "c3" ? unit.change_c3_pct : unit.change_overall_pct;
            return (
              <tr key={unit.name} className={unit.home ? "bg-accent/5" : ""}>
                <td className="whitespace-nowrap font-semibold text-ink">
                  <Link href={poldaHref(unit.name)} scroll={false} className="hover:text-accent">
                    {unit.name}
                  </Link>
                </td>
                {years.flatMap((year) => {
                  const row = unit[scope][year];
                  return [
                    <td key={`${year}-ct`} className="text-right tabular-nums">
                      {angka(row?.ct)}
                    </td>,
                    compact ? null : (
                      <td key={`${year}-cc`} className="text-right tabular-nums text-ink-muted">
                        {angka(row?.cc)}
                      </td>
                    ),
                    <td key={`${year}-cr`} className="text-right tabular-nums text-ink-muted">
                      {persen(row?.cr)}
                    </td>,
                  ];
                })}
                {compact ? null : <td className="text-right tabular-nums">{perubahan(change)}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TabelBulan({
  recap,
  years,
  label,
}: {
  recap: Ready;
  years: string[];
  label: (year: string) => string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Bulan</th>
            {years.map((year) => (
              <th key={`o-${year}`} className="text-right">
                Semua {label(year)}
              </th>
            ))}
            {years.map((year) => (
              <th key={`c-${year}`} className="text-right">
                3C {label(year)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {recap.monthly.map((row) => (
            <tr key={row.month}>
              <td>{BULAN[row.month - 1]}</td>
              {years.map((year) => (
                <td key={`o-${year}`} className="text-right tabular-nums">
                  {angka(row.overall[year])}
                </td>
              ))}
              {years.map((year) => (
                <td key={`c-${year}`} className="text-right tabular-nums">
                  {angka(row.c3[year])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Rincian satu satuan: dibuka dari klik pada peta (halaman ini, Beranda, atau Peta) atau dari
 * nama pada tabel. Isinya hanya yang ada pada rekap — jumlah per tahun, bukan kelurahan.
 */
function RincianSatuan({
  unit,
  recap,
  years,
  label,
}: {
  unit: RecapUnit;
  recap: Ready;
  years: string[];
  label: (year: string) => string;
}) {
  const current = String(recap.current_year);
  return (
    <Panel
      title={`Rincian · ${unit.name}`}
      action={
        <Link href="/ops/polda" scroll={false} className="panel-action">
          Tutup rincian
        </Link>
      }
      bodyClassName="flex flex-col gap-3"
    >
      <p className="text-xs leading-relaxed text-ink">
        {unit.kind === "POLRES"
          ? `Pada ${label(current)}: 3C ${angka(unit.c3[current]?.ct)} laporan (${persen(unit.c3[current]?.share_pct)} dari 3C Polda), peringkat ${unit.rank_c3} dari ${recap.polres_count} Polres; kriminal keseluruhan ${angka(unit.overall[current]?.ct)} laporan (${persen(unit.overall[current]?.share_pct)} dari Polda), peringkat ${unit.rank_overall}.`
          : `Satuan kerja tingkat Polda. Pada ${label(current)}: kriminal keseluruhan ${angka(unit.overall[current]?.ct)} laporan, 3C ${angka(unit.c3[current]?.ct)} laporan.`}{" "}
        Perubahan periode setara {recap.current_year} terhadap tahun sebelumnya: 3C{" "}
        {perubahan(unit.change_c3_pct)}, keseluruhan {perubahan(unit.change_overall_pct)}.
      </p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Tahun</th>
              <th className="text-right">Keseluruhan CT</th>
              <th className="text-right">CC</th>
              <th className="text-right">CR</th>
              <th className="text-right">3C CT</th>
              <th className="text-right">CC</th>
              <th className="text-right">CR</th>
              <th className="text-right">Curat</th>
              <th className="text-right">Curas</th>
              <th className="text-right">Curanmor</th>
              <th className="text-right">3C dari keseluruhan</th>
              <th className="text-right">Porsi 3C Polda</th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => (
              <tr key={year}>
                <td className="font-semibold text-ink">{label(year)}</td>
                <td className="text-right tabular-nums">{angka(unit.overall[year]?.ct)}</td>
                <td className="text-right tabular-nums text-ink-muted">
                  {angka(unit.overall[year]?.cc)}
                </td>
                <td className="text-right tabular-nums text-ink-muted">
                  {persen(unit.overall[year]?.cr)}
                </td>
                <td className="text-right tabular-nums">{angka(unit.c3[year]?.ct)}</td>
                <td className="text-right tabular-nums text-ink-muted">
                  {angka(unit.c3[year]?.cc)}
                </td>
                <td className="text-right tabular-nums text-ink-muted">
                  {persen(unit.c3[year]?.cr)}
                </td>
                <td className="text-right tabular-nums">{angka(unit.c3[year]?.curat)}</td>
                <td className="text-right tabular-nums">{angka(unit.c3[year]?.curas)}</td>
                <td className="text-right tabular-nums">{angka(unit.c3[year]?.curanmor)}</td>
                <td className="text-right tabular-nums text-ink-muted">
                  {persen(unit.c3[year]?.of_overall_pct)}
                </td>
                <td className="text-right tabular-nums text-ink-muted">
                  {persen(unit.c3[year]?.share_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-2xs leading-relaxed text-ink-faint">
        {unit.home
          ? "Rincian sampai kelurahan untuk satuan ini ada pada Peta dan Analitik (dihitung dari data per kejadian, menurut tanggal kejadian — angkanya berbeda dasar dengan rekap ini)."
          : "Untuk satuan ini yang tersedia hanya rekap per tahun; data per kejadian, kecamatan, dan kelurahannya tidak ada pada sistem."}
      </p>
    </Panel>
  );
}

/**
 * Peta tingkat Polda yang diwarnai menurut jumlah laporan 3C. Warna hanya penanda urutan;
 * angkanya tertulis pada label dan tabel di sampingnya. Digambar di server (SVG polos);
 * tiap Polres adalah tautan ke rinciannya.
 */
function PetaPolres({
  units,
  year,
  chosen,
}: {
  units: RecapUnit[];
  year: string;
  chosen: string | null;
}) {
  const shapes = shapesAt("polda");
  const byArea = new Map(
    units.flatMap((unit) => {
      const area = UNIT_AREA[unit.name];
      return area ? [[area, unit] as const] : [];
    }),
  );
  const highest = Math.max(1, ...[...byArea.values()].map((unit) => unit.c3[year]?.ct ?? 0));
  const offMap = units.filter((unit) => {
    const area = UNIT_AREA[unit.name];
    return !area || OFF_FRAME_AREAS.includes(area);
  });
  return (
    <div>
      <svg
        viewBox={viewBoxOf(shapes, 0.03)}
        role="img"
        aria-label={`Peta jumlah laporan 3C per Polres tahun ${year}`}
        className="h-auto w-full"
      >
        {shapes.map((shape) => {
          const unit = byArea.get(shape.name);
          const count = unit?.c3[year]?.ct ?? null;
          const marked = unit !== undefined && (unit.home || unit.name === chosen);
          const drawn = (
            <>
              <title>
                {unit
                  ? `${unit.name}: ${angka(count)} laporan 3C — klik untuk rincian`
                  : `${shape.name}: tidak ada pada rekap`}
              </title>
              {shape.rings.map((ring) => (
                <polygon
                  key={polygonPoints(ring).slice(0, 48)}
                  points={polygonPoints(ring)}
                  className={
                    unit
                      ? marked
                        ? "fill-accent stroke-accent-deep"
                        : "fill-accent stroke-base-600"
                      : "fill-base-800 stroke-base-600"
                  }
                  fillOpacity={count === null ? 1 : 0.12 + 0.78 * (count / highest)}
                  strokeWidth={unit?.name === chosen ? 70 : unit?.home ? 45 : 10}
                />
              ))}
            </>
          );
          return unit ? (
            <a key={shape.name} href={poldaHref(unit.name)} aria-label={`Rincian ${unit.name}`}>
              {drawn}
            </a>
          ) : (
            <g key={shape.name}>{drawn}</g>
          );
        })}
        {shapes.map((shape) => {
          const unit = byArea.get(shape.name);
          if (!unit || OFF_FRAME_AREAS.includes(shape.name)) return null;
          return (
            <text
              key={`t-${shape.name}`}
              x={shape.label[0]}
              y={shape.label[1]}
              textAnchor="middle"
              pointerEvents="none"
              className="fill-ink font-heading font-semibold"
              style={{ fontSize: 290, paintOrder: "stroke" }}
              stroke="rgb(var(--base-900))"
              strokeWidth={70}
            >
              {angka(unit.c3[year]?.ct)}
            </text>
          );
        })}
      </svg>
      <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
        Makin pekat, makin banyak laporan 3C; garis tebal = {units.find((unit) => unit.home)?.name}
        {chosen ? ` dan satuan yang sedang dibuka` : ""}. Klik sebuah Polres untuk rinciannya.
        Wilayah abu-abu tidak tercantum sebagai satuan tersendiri pada rekap.
        {offMap.length > 0
          ? ` Tidak digambar pada peta (buka dari tabel): ${offMap
              .map((unit) => `${unit.name} (${angka(unit.c3[year]?.ct)})`)
              .join(", ")}.`
          : ""}{" "}
        © Kontributor OpenStreetMap.
      </p>
    </div>
  );
}

/** Keadaan tidak berwenang — dinyatakan, bukan disamarkan sebagai halaman kosong. */
function TidakBerwenang() {
  return (
    <div className="mx-auto max-w-2xl">
      <Panel title="Polda Metro Jaya">
        <div className="rounded border border-risk-moderate/40 bg-risk-moderate/5 px-4 py-3">
          <div className="stat-label text-risk-moderate">Tidak berwenang</div>
          <p className="mt-1 text-sm leading-relaxed text-ink">
            Rekap per Polres hanya untuk akun yang analitiknya mencakup seluruh wilayah. Permintaan
            ditolak backend dan percobaannya tercatat pada audit trail.
          </p>
        </div>
      </Panel>
    </div>
  );
}
