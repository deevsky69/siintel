import Link from "next/link";
import { LevelBadge, MonthBars, Stars } from "@/components/warga/bits";
import { type MapAreaDatum, PublicMap } from "@/components/warga/public-map";
import {
  type AreaLevel,
  getBabinContact,
  getPublicSummary,
  LEVEL_LABEL,
  longMonth,
  threatLabel,
} from "@/lib/warga";

export const metadata = { title: "Peta Wilayah — SIGAP WARGA" };
export const dynamic = "force-dynamic";

const LEVELS: AreaLevel[] = ["TINGGI", "SEDANG", "RENDAH"];

/**
 * Peta wilayah untuk warga — panggung selebar layar (mockup 10 November 2026).
 *
 * Tiga kolom di layar lebar: panel kiri (cari wilayah, saring tingkat, daftar kecamatan
 * atau kelurahan), peta di tengah di atas kanvas abu bergaris putih, kartu rincian di kanan
 * yang dapat dilipat. Di ponsel ketiganya bertumpuk. Alamat menyimpan pilihan
 * (`?kecamatan=&kelurahan=&tingkat=&q=`) supaya dapat dibagikan dan tombol kembali
 * peramban bekerja. Isinya hanya yang diputuskan boleh terbuka: jumlah historis, tingkat
 * kasar, nilai rasa aman, dan kontak Babinkamtibmas.
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
      <div className="warga-wrap py-10">
        <p className="warga-card p-6 text-sm text-ink-muted">
          Peta belum dapat dimuat. Coba lagi sebentar.
        </p>
      </div>
    );
  }

  // Kotak cari dari beranda/panel: nama kelurahan atau kecamatan, tidak peduli huruf besar.
  const q = one("q").trim().toLowerCase();
  const foundArea = q ? summary.areas.find((row) => row.kelurahan.toLowerCase() === q) : null;
  const foundKec = q ? summary.kecamatan.find((row) => row.kecamatan.toLowerCase() === q) : null;
  const partial =
    q && !foundArea && !foundKec
      ? (summary.areas.find((row) => row.kelurahan.toLowerCase().includes(q)) ??
        summary.areas.find((row) => row.kecamatan.toLowerCase().includes(q)))
      : null;

  const kecamatanNames = new Set(summary.kecamatan.map((row) => row.kecamatan));
  const kecamatan =
    foundArea?.kecamatan ??
    foundKec?.kecamatan ??
    (partial?.kelurahan.toLowerCase().includes(q) ? partial.kecamatan : null) ??
    (kecamatanNames.has(one("kecamatan")) ? one("kecamatan") : "");
  const wantedKel = foundArea?.kelurahan ?? partial?.kelurahan ?? one("kelurahan");
  const area = summary.areas.find(
    (row) => row.kelurahan === wantedKel && (!kecamatan || row.kecamatan === kecamatan),
  );
  const kecRow = summary.kecamatan.find((row) => row.kecamatan === kecamatan) ?? null;
  const tingkat = LEVELS.find((level) => level === one("tingkat").toUpperCase()) ?? null;
  const babin = area
    ? await getBabinContact(area.kelurahan)
        .then((r) => r.data)
        .catch(() => null)
    : null;

  const rows = kecamatan
    ? summary.areas.filter((row) => row.kecamatan === kecamatan)
    : summary.kecamatan;
  const data = new Map<string, MapAreaDatum>(
    kecamatan
      ? summary.areas
          .filter((row) => row.kecamatan === kecamatan)
          .map((row) => [row.kelurahan, { level: row.level, total: row.total }])
      : summary.kecamatan.map((row) => [row.kecamatan, { level: row.level, total: row.total }]),
  );
  const hrefFor = (name: string, level: AreaLevel | null = tingkat) => {
    const query = new URLSearchParams();
    if (kecamatan) {
      query.set("kecamatan", kecamatan);
      query.set("kelurahan", name);
    } else {
      query.set("kecamatan", name);
    }
    if (level) query.set("tingkat", level);
    return `/peta?${query.toString()}`;
  };
  const filterHref = (level: AreaLevel | null) => {
    const query = new URLSearchParams();
    if (kecamatan) query.set("kecamatan", kecamatan);
    if (area) query.set("kelurahan", area.kelurahan);
    if (level) query.set("tingkat", level);
    const text = query.toString();
    return text ? `/peta?${text}` : "/peta";
  };
  const highInKec = kecRow
    ? summary.areas
        .filter((row) => row.kecamatan === kecRow.kecamatan && row.level === "TINGGI")
        .map((row) => row.kelurahan)
    : [];
  const period = `${longMonth(summary.window_from)} – ${longMonth(summary.window_to)}`;
  const counts: Record<AreaLevel, number> = { TINGGI: 0, SEDANG: 0, RENDAH: 0 };
  for (const row of rows) counts[row.level] += 1;

  return (
    <div className="warga-bleed warga-stage">
      <aside className="warga-panel lg:max-h-[740px]">
        <div className="warga-panel-head">
          <form action="/peta" method="get" className="flex flex-col gap-1.5">
            <label htmlFor="loc" className="text-[13px] font-bold text-[rgb(var(--warga-navy))]">
              Cari wilayah
            </label>
            <div className="flex min-h-[46px] items-center gap-2.5 border-[1.5px] border-base-700 bg-base-950 px-3">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
                className="text-ink-faint"
              >
                <path d="M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zm5 11.5L20 20" />
              </svg>
              <input
                id="loc"
                name="q"
                type="search"
                defaultValue={one("q")}
                placeholder="Kelurahan atau kecamatan"
                className="min-w-0 flex-1 border-0 bg-transparent text-[15px] text-[rgb(var(--warga-navy))] outline-none"
              />
            </div>
          </form>
          <fieldset className="m-0 flex flex-wrap gap-1 border-0 p-0">
            <legend className="sr-only">Saring tingkat</legend>
            <Link href={filterHref(null)} className="warga-chip" aria-pressed={tingkat === null}>
              Semua <b>{rows.length}</b>
            </Link>
            {LEVELS.map((level) => (
              <Link
                key={level}
                href={filterHref(level)}
                className={`warga-chip is-${level.toLowerCase()}`}
                aria-pressed={tingkat === level}
              >
                <i aria-hidden="true" />
                {LEVEL_LABEL[level]} <b>{counts[level]}</b>
              </Link>
            ))}
          </fieldset>
          <p className="text-xs text-ink-faint">Periode {period}</p>
        </div>
        <nav aria-label="Jejak" className="warga-crumb px-4 pt-3">
          <Link href="/peta">Jakarta Selatan</Link>
          {kecamatan ? (
            <>
              <span>›</span>
              <Link href={`/peta?kecamatan=${encodeURIComponent(kecamatan)}`}>{kecamatan}</Link>
            </>
          ) : null}
          {area ? (
            <>
              <span>›</span>
              <span className="font-semibold text-ink">{area.kelurahan}</span>
            </>
          ) : null}
        </nav>
        <ul className="flex-1 overflow-y-auto p-2">
          {rows
            .filter((row) => tingkat === null || row.level === tingkat)
            .map((row) => {
              const name =
                "kelurahan" in row && typeof row.kelurahan === "string"
                  ? row.kelurahan
                  : row.kecamatan;
              const current = area?.kelurahan === name;
              return (
                <li key={name}>
                  <Link
                    href={hrefFor(name)}
                    className="warga-panel-item"
                    aria-current={current ? "true" : undefined}
                  >
                    <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="text-[15px] font-semibold text-[rgb(var(--warga-navy))]">
                        {name}
                      </span>
                      <span className="text-xs text-ink-faint">
                        {row.total} kejadian · 12 bulan
                      </span>
                    </span>
                    <LevelBadge level={row.level} />
                  </Link>
                </li>
              );
            })}
        </ul>
      </aside>

      <section className="warga-map-surface min-h-[320px] p-4 sm:p-6" aria-label="Peta">
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
          emphasis={tingkat}
          tip
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <ul className="warga-legend" aria-label="Keterangan warna">
            <li>
              <i style={{ background: "#BFD7EA" }} /> Rendah
            </li>
            <li>
              <i style={{ background: "#F2B45A" }} /> Sedang
            </li>
            <li>
              <i style={{ background: "#EA580C" }} /> Tinggi
            </li>
          </ul>
          <span className="warga-period">
            {period} · dihitung dari kejadian tercatat, bukan prediksi
          </span>
        </div>
      </section>

      <section className="warga-panel" aria-live="polite">
        <details open className="group">
          <summary className="flex min-h-[56px] cursor-pointer list-none items-center gap-3 px-4 py-2.5">
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-ink-faint">
                {area ? "Kelurahan" : kecRow ? "Kecamatan" : "Wilayah"}
              </span>
              <span className="truncate text-[17px] font-extrabold text-[rgb(var(--warga-navy))]">
                {area?.kelurahan ?? kecRow?.kecamatan ?? "Jakarta Selatan"}
              </span>
            </span>
            {area ? (
              <LevelBadge level={area.level} />
            ) : kecRow ? (
              <LevelBadge level={kecRow.level} />
            ) : null}
            <span className="text-[13px] font-bold text-accent-soft group-open:hidden">
              Rincian
            </span>
            <span className="hidden text-[13px] font-bold text-accent-soft group-open:inline">
              Tutup
            </span>
          </summary>
          <div className="flex flex-col gap-3 border-t border-base-850 px-4 pb-4 pt-3.5">
            {area ? (
              <>
                <p className="text-xs text-ink-faint">
                  {area.kecamatan} · Polsek {area.polsek ?? "—"}
                </p>
                <dl className="grid grid-cols-2 gap-3">
                  <div className="bg-base-950 px-4 py-3">
                    <dt className="text-xs text-ink-muted">Kejadian 12 bulan</dt>
                    <dd className="text-2xl font-extrabold tabular-nums text-[rgb(var(--warga-navy))]">
                      {area.total}
                    </dd>
                  </div>
                  <div className="bg-base-950 px-4 py-3">
                    <dt className="text-xs text-ink-muted">Rasa aman warga</dt>
                    <dd className="flex flex-wrap items-center gap-1.5">
                      <Stars value={area.rating} size="text-sm" />
                      <span className="text-xs text-ink-muted">
                        {area.rating_count > 0
                          ? `${area.rating} · ${area.rating_count} ulasan`
                          : "belum ada"}
                      </span>
                    </dd>
                  </div>
                </dl>
                <div>
                  <p className="text-[13px] font-bold text-[rgb(var(--warga-navy))]">
                    Kejadian per jenis · 12 bulan
                  </p>
                  <ul>
                    {Object.entries(area.by_threat).map(([threat, count]) => (
                      <li
                        key={threat}
                        className="flex items-center justify-between border-b border-base-850 py-2 text-sm last:border-b-0"
                      >
                        <span>{threatLabel(threat)}</span>
                        <span className="font-bold tabular-nums text-ink-faint">{count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <MonthBars months={summary.months} values={area.by_month} />
                {babin ? (
                  <div className="warga-babin">
                    <span className="warga-babin-icon" aria-hidden="true">
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        role="img"
                        aria-label="Telepon"
                      >
                        <title>Telepon</title>
                        <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" />
                      </svg>
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-ink-faint">
                        Babinkamtibmas{babin.is_dummy ? " · data peragaan" : ""}
                      </p>
                      <p className="text-sm font-bold text-[rgb(var(--warga-navy))]">
                        {babin.rank ? `${babin.rank} ` : ""}
                        {babin.name} ·{" "}
                        <a
                          href={`tel:${babin.phone_display.replace(/[^0-9+]/g, "")}`}
                          className="text-accent-soft"
                        >
                          {babin.phone_display}
                        </a>
                      </p>
                      {babin.whatsapp_group_link &&
                      /^https:\/\/chat\.whatsapp\.com\//.test(babin.whatsapp_group_link) ? (
                        <a
                          href={babin.whatsapp_group_link}
                          className="text-xs font-semibold text-accent-soft"
                          rel="noreferrer"
                          target="_blank"
                        >
                          Grup warga ↗
                        </a>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/survey?kelurahan=${encodeURIComponent(area.kelurahan)}`}
                    className="warga-btn warga-btn-sm warga-btn-primary flex-1"
                  >
                    Tandai rasa aman
                  </Link>
                  <Link href="/lapor" className="warga-btn warga-btn-sm warga-btn-ghost flex-1">
                    Lapor di wilayah ini
                  </Link>
                </div>
                <Link
                  href={`/peta?kecamatan=${encodeURIComponent(area.kecamatan)}`}
                  className="text-center text-[13px] text-ink-faint underline-offset-2 hover:underline"
                >
                  Kembali ke kecamatan {area.kecamatan}
                </Link>
              </>
            ) : kecRow ? (
              <>
                <p className="text-sm leading-relaxed text-ink-muted">
                  {kecRow.total} kejadian tercatat di {kecRow.kelurahan} kelurahan dalam dua belas
                  bulan terakhir. Ketuk kelurahan pada peta atau daftar untuk rinciannya.
                </p>
                <div>
                  <p className="text-[13px] font-bold text-[rgb(var(--warga-navy))]">
                    Kejadian per jenis · 12 bulan
                  </p>
                  <ul>
                    {Object.entries(kecRow.by_threat).map(([threat, count]) => (
                      <li
                        key={threat}
                        className="flex items-center justify-between border-b border-base-850 py-2 text-sm last:border-b-0"
                      >
                        <span>{threatLabel(threat)}</span>
                        <span className="font-bold tabular-nums text-ink-faint">{count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                {highInKec.length > 0 ? (
                  <p className="warga-warn">
                    <strong>Kelurahan rawan tinggi:</strong> {highInKec.join(", ")}
                  </p>
                ) : null}
                <Link href="/lapor" className="warga-btn warga-btn-sm warga-btn-primary">
                  Lapor kejadian di wilayah ini
                </Link>
                <Link
                  href="/peta"
                  className="warga-btn warga-btn-sm warga-btn-ghost !border-base-700 !text-ink-faint"
                >
                  Hapus pilihan · tampilkan semua wilayah
                </Link>
              </>
            ) : (
              <p className="text-sm leading-relaxed text-ink-muted">
                Ketuk kecamatan pada peta, atau pilih dari daftar di panel kiri, untuk melihat
                jumlah kejadian per jenis, kelurahan rawan, dan kontak Babinkamtibmas.
              </p>
            )}
          </div>
        </details>
      </section>
    </div>
  );
}
