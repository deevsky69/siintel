"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { type AreaLevel, LEVEL_LABEL, longMonth, type PublicSummary } from "@/lib/warga";
import { type MapAreaDatum, PublicMap } from "./public-map";

export type ImbauanRow = {
  code: string;
  threat_type: string;
  area_text: string;
  time_window: string | null;
  message: string;
};

const LEVELS: AreaLevel[] = ["TINGGI", "SEDANG", "RENDAH"];
const STAT_COLOR: Record<AreaLevel, string> = {
  TINGGI: "#EA580C",
  SEDANG: "#F2B45A",
  RENDAH: "#BFD7EA",
};

/**
 * Hero beranda SIGAP WARGA (mockup 10 November 2026): bidang navy selebar layar. Kiri —
 * pil periode, judul, penjelasan, kotak cari wilayah, tiga angka jumlah kecamatan per
 * tingkat. Kanan — kartu putih berisi peta kecamatan dengan chip saring, periode, legenda,
 * dan tautan ke peta lengkap. Di bawahnya strip **Imbauan Polres** yang menumpang di tepi
 * hero, dengan tombol Lapor kejadian dan Darurat 110.
 *
 * Yang berpindah ke komponen klien ini hanya keadaan tampilan: chip yang dipilih meredupkan
 * wilayah lain, dan wilayah yang disentuh memunculkan kartu kecil. Datanya dari Server
 * Component; tidak ada skor, prediksi, maupun titik kejadian.
 */
export function MapCanvas({
  summary,
  imbauan,
}: {
  summary: PublicSummary | null;
  imbauan: ImbauanRow[];
}) {
  const [emphasis, setEmphasis] = useState<AreaLevel | null>(null);
  const data = useMemo(
    () =>
      new Map<string, MapAreaDatum>(
        (summary?.kecamatan ?? []).map((row) => [
          row.kecamatan,
          { level: row.level, total: row.total },
        ]),
      ),
    [summary],
  );
  const counts = useMemo(() => {
    const out: Record<AreaLevel, number> = { TINGGI: 0, SEDANG: 0, RENDAH: 0 };
    for (const row of summary?.kecamatan ?? []) out[row.level] += 1;
    return out;
  }, [summary]);
  const period = summary
    ? `${longMonth(summary.window_from)} – ${longMonth(summary.window_to)}`
    : null;

  return (
    <>
      <section className="warga-hero" aria-label="Keadaan wilayah">
        <div className="warga-wrap flex flex-wrap items-stretch gap-10 pb-16 pt-12 sm:pt-14">
          <div className="flex min-w-0 flex-[1_1_420px] flex-col justify-center gap-6">
            <span className="warga-pill self-start">
              Keadaan wilayah{period ? ` · ${period}` : ""}
            </span>
            <h1 className="text-4xl text-white sm:text-5xl lg:text-[56px] lg:leading-[1.05]">
              Keadaan wilayah Jakarta Selatan
            </h1>
            <p className="max-w-[520px] text-lg leading-relaxed text-[rgb(var(--warga-soft))]">
              Peta ini menampilkan tingkat kerawanan per kecamatan dan kelurahan berdasarkan
              ringkasan data dua belas bulan terakhir. Pilih wilayah untuk melihat rinciannya.
            </p>
            <form action="/peta" method="get" className="flex max-w-[560px] flex-wrap gap-2">
              <label htmlFor="cari-wilayah" className="sr-only">
                Cari wilayah
              </label>
              <div className="flex min-h-[52px] flex-[1_1_280px] items-center bg-white px-4">
                <input
                  id="cari-wilayah"
                  name="q"
                  type="search"
                  placeholder="Cari kelurahan atau kecamatan"
                  className="min-w-0 flex-1 border-0 bg-transparent text-base text-[rgb(var(--warga-navy))] outline-none placeholder:text-ink-faint"
                />
              </div>
              <button type="submit" className="warga-btn warga-btn-gold min-h-[52px]">
                Lihat di peta
              </button>
            </form>
            {summary ? (
              <dl className="flex flex-wrap gap-3">
                {LEVELS.map((level) => (
                  <div key={level} className="flex-[1_1_140px] py-1">
                    <dt className="text-[13px] text-[rgb(var(--warga-soft))]">
                      {LEVEL_LABEL[level]}
                    </dt>
                    <dd
                      className="mt-1 text-[40px] font-extrabold leading-none"
                      style={{ color: STAT_COLOR[level] }}
                    >
                      {counts[level]}{" "}
                      <span className="text-sm font-medium text-[rgb(var(--warga-soft))]">
                        kecamatan
                      </span>
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>

          <div className="flex min-w-0 flex-[1_1_520px] flex-col gap-4 bg-white p-5 text-ink">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-base font-bold text-[rgb(var(--warga-navy))]">
                Tingkat kerawanan per kecamatan
              </span>
              {summary ? (
                <fieldset className="m-0 flex min-w-0 flex-wrap gap-1.5 border-0 p-0">
                  <legend className="sr-only">Saring tingkat</legend>
                  <button
                    type="button"
                    className="warga-chip"
                    aria-pressed={emphasis === null}
                    onClick={() => setEmphasis(null)}
                  >
                    Semua
                    <b>{summary.kecamatan.length}</b>
                  </button>
                  {LEVELS.map((level) => (
                    <button
                      key={level}
                      type="button"
                      className={`warga-chip is-${level.toLowerCase()}`}
                      aria-pressed={emphasis === level}
                      onClick={() => setEmphasis((current) => (current === level ? null : level))}
                    >
                      <i aria-hidden="true" />
                      {LEVEL_LABEL[level]}
                      <b>{counts[level]}</b>
                    </button>
                  ))}
                </fieldset>
              ) : null}
            </div>
            <div className="warga-map-surface p-3 sm:p-4">
              {summary ? (
                <PublicMap
                  level="kecamatan"
                  data={data}
                  hrefPrefix="/peta?kecamatan="
                  emphasis={emphasis}
                  tip
                />
              ) : (
                <div className="flex min-h-[260px] flex-col items-center justify-center gap-2 p-6 text-center">
                  <p className="text-sm font-semibold text-ink">Peta belum dapat dimuat.</p>
                  <p className="text-xs text-ink-muted">
                    Coba muat ulang halaman. Laporan dan nomor darurat tetap dapat dipakai.
                  </p>
                </div>
              )}
              {period ? (
                <span className="warga-period absolute bottom-3 left-3">Periode: {period}</span>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
              <ul className="warga-legend" aria-label="Keterangan warna">
                <li>
                  <i style={{ background: STAT_COLOR.RENDAH }} /> Rendah
                </li>
                <li>
                  <i style={{ background: STAT_COLOR.SEDANG }} /> Sedang
                </li>
                <li>
                  <i style={{ background: STAT_COLOR.TINGGI }} /> Tinggi
                </li>
              </ul>
              <Link
                href="/peta"
                className="warga-link inline-flex min-h-[44px] items-center text-sm"
              >
                Buka peta lengkap →
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="warga-wrap relative -mt-7" aria-label="Imbauan Polres">
        <div className="warga-card-raised flex flex-wrap items-center gap-x-6 gap-y-4 px-6 py-5">
          <div className="min-w-0 flex-[1_1_320px]">
            <p className="warga-eyebrow text-xs">Imbauan Polres</p>
            {imbauan.length === 0 ? (
              <p className="mt-0.5 text-base text-[rgb(var(--warga-navy))]">
                Tidak ada imbauan khusus saat ini. Tetap waspada dan kunci kendaraan Anda.
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {imbauan.slice(0, 3).map((row) => (
                  <li key={row.code} className="warga-alert">
                    <div className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
                      <span className="font-bold uppercase tracking-wide text-risk-high">
                        {row.threat_type}
                      </span>
                      <span className="text-ink-muted">{row.area_text}</span>
                      {row.time_window ? (
                        <span className="text-ink-faint">{row.time_window} WIB</span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm leading-snug text-ink">{row.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Link href="/lapor" className="warga-btn warga-btn-sm warga-btn-primary">
              Lapor kejadian
            </Link>
            <a href="tel:110" className="warga-btn warga-btn-sm warga-btn-danger-outline">
              Darurat · 110
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
