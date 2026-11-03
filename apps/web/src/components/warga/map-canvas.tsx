"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { type AreaLevel, LEVEL_LABEL, longMonth, type PublicSummary } from "@/lib/warga";
import { BersamaRing } from "./brand";
import { type MapAreaDatum, PublicMap } from "./public-map";

export type ImbauanRow = {
  code: string;
  threat_type: string;
  area_text: string;
  time_window: string | null;
  message: string;
};

const LEVELS: AreaLevel[] = ["TINGGI", "SEDANG", "RENDAH"];

/**
 * Kanvas beranda SIGAP WARGA (3 November 2026) — peta sebagai meja kerja, panel di atasnya.
 *
 * Polanya mengikuti dasbor peringatan lingkungan (peta penuh + panel mengambang berisi
 * chip saring dan kartu peringatan; di ponsel, peta di atas dan lembar informasi naik dari
 * bawah). Yang berpindah tangan ke komponen klien ini hanya keadaan tampilan: chip tingkat
 * yang dipilih meredupkan wilayah lain, dan wilayah yang disentuh memunculkan kartu kecil.
 * Datanya tetap datang dari Server Component (`page.tsx`).
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

  return (
    <section className="warga-canvas" aria-label="Keadaan wilayah">
      <div className="warga-canvas-map">
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
        {summary ? (
          <ul className="warga-legend" aria-label="Keterangan warna">
            <li>
              <i className="bg-risk-low" /> Rendah
            </li>
            <li>
              <i className="bg-risk-moderate" /> Sedang
            </li>
            <li>
              <i className="bg-risk-high" /> Tinggi
            </li>
          </ul>
        ) : null}
      </div>

      <div className="warga-float">
        <div className="warga-sheet-handle sm:hidden" aria-hidden="true" />
        <div className="flex items-center gap-3">
          <BersamaRing size={64} light />
          <div className="min-w-0">
            <p className="warga-eyebrow">Polres Metro Jakarta Selatan</p>
            <h1 className="mt-0.5 text-[1.35rem] font-extrabold leading-tight text-ink">
              Lihat keadaan wilayahmu
            </h1>
          </div>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-ink-muted">
          Warna peta adalah tingkat kerawanan kasar dua belas bulan terakhir per kecamatan.
          {summary ? (
            <>
              {" "}
              <span className="text-ink-faint">
                {longMonth(summary.window_from)} – {longMonth(summary.window_to)}.
              </span>
            </>
          ) : null}
        </p>

        {summary ? (
          <fieldset className="m-0 mt-3 flex min-w-0 flex-wrap gap-1.5 border-0 p-0">
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

        <div className="mt-4 flex items-baseline justify-between">
          <h2 className="text-sm font-bold text-ink">Imbauan berlaku</h2>
          <span className="text-[11px] text-ink-faint">dari Polres</span>
        </div>
        {imbauan.length === 0 ? (
          <p className="warga-alert-empty mt-2">
            Tidak ada imbauan khusus saat ini. Tetap waspada dan kunci kendaraan Anda.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {imbauan.slice(0, 3).map((row, index) => (
              <li
                key={row.code}
                className="warga-alert"
                style={{ animationDelay: `${320 + index * 90}ms` }}
              >
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

        <div className="mt-4 grid grid-cols-2 gap-2">
          <Link href="/lapor" className="warga-btn warga-btn-amber">
            Lapor kejadian
          </Link>
          <a href="tel:110" className="warga-btn warga-btn-danger">
            Darurat · 110
          </a>
        </div>
      </div>
    </section>
  );
}
