import Link from "next/link";
import { LevelBadge, Stars } from "@/components/warga/bits";
import { MapCanvas } from "@/components/warga/map-canvas";
import { Reveal } from "@/components/warga/reveal";
import { getPublicSummary, highlightAreas, longMonth } from "@/lib/warga";
import { getImbauanPublik } from "./lapor/actions";

export const metadata = { title: "SIGAP WARGA — Polres Metro Jakarta Selatan" };
export const dynamic = "force-dynamic";

/**
 * Beranda SIGAP WARGA (2 November 2026; dirombak 3 November 2026).
 *
 * Susunan: kanvas peta dengan panel keadaan wilayah di atasnya (MapCanvas), empat jalan
 * pintas, lalu Survey Rasa Aman dan wilayah berkerawanan tinggi. Yang tampil: imbauan yang
 * sudah diterbitkan, tingkat kerawanan kasar per kecamatan, dan sorotan survey. Tidak ada
 * skor, prediksi, maupun titik kejadian: keputusan pemilik proyek, "sederhana saja untuk
 * masyarakat".
 */
export default async function BerandaWarga() {
  const [summary, imbauan] = await Promise.all([
    getPublicSummary().catch(() => null),
    getImbauanPublik().catch(() => []),
  ]);
  const highlights = summary ? highlightAreas(summary) : [];
  const highAreas = summary
    ? summary.areas
        .filter((area) => area.level === "TINGGI")
        .sort((a, b) => b.total - a.total)
        .slice(0, 6)
    : [];

  return (
    <div className="space-y-6">
      <MapCanvas summary={summary} imbauan={imbauan} />

      <Reveal>
        <nav aria-label="Jalan pintas" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Shortcut
            href="/lacak"
            title="Lacak laporan"
            text="Nomor LP dan PIN pelapor"
            icon="M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zm5 11.5L20 20"
          />
          <Shortcut
            href="/lacak?tab=kendaraan"
            title="Cek kendaraan bekas"
            text="Plat atau nomor rangka tercatat?"
            icon="M5 16V9l2-4h10l2 4v7M5 16h14M5 16v2m14-2v2M8 12h.01M16 12h.01"
          />
          <Shortcut
            href="/survey"
            title="Survey Rasa Aman"
            text="Nilai kelurahanmu, anonim"
            icon="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z"
          />
          <Shortcut
            href="/peta"
            title="Peta kelurahan"
            text="Angka per bulan dan kontak Babin"
            icon="M9 4 3 6.5v13L9 17l6 2.5 6-2.5v-13L15 6.5zm0 0v13m6-10.5v13"
          />
        </nav>
      </Reveal>

      <Reveal delay={60}>
        <section className="grid gap-4 md:grid-cols-2">
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
            {highlights.length > 0 ? (
              <ul className="mt-3 divide-y divide-base-800">
                {highlights.map((area) => (
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
                    <span className="text-xs tabular-nums text-ink-muted">
                      ({area.rating_count})
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">
                Belum ada ulasan yang tayang. Jadilah yang pertama menilai kelurahan Anda.
              </p>
            )}
          </div>

          <div className="warga-card p-5">
            <h2 className="text-base font-bold text-ink">Wilayah dengan kerawanan tinggi</h2>
            {summary ? (
              <>
                <p className="mt-1 text-xs text-ink-muted">
                  {longMonth(summary.window_from)} – {longMonth(summary.window_to)} · pencurian
                  kendaraan, pencurian dengan pemberatan, dan dengan kekerasan.
                </p>
                {highAreas.length > 0 ? (
                  <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                    {highAreas.map((area) => (
                      <li key={area.kelurahan}>
                        <Link
                          href={`/peta?kecamatan=${encodeURIComponent(area.kecamatan)}&kelurahan=${encodeURIComponent(area.kelurahan)}`}
                          className="warga-row"
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-semibold text-ink">
                              {area.kelurahan}
                            </span>
                            <span className="text-xs text-ink-faint">{area.kecamatan}</span>
                          </span>
                          <LevelBadge level={area.level} />
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-ink-muted">
                    Tidak ada kelurahan bertingkat tinggi pada rentang ini.
                  </p>
                )}
                <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">{summary.basis}</p>
              </>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">
                Ringkasan wilayah belum dapat dimuat. Coba lagi beberapa saat.
              </p>
            )}
          </div>
        </section>
      </Reveal>
    </div>
  );
}

/** Jalan pintas: ikon, judul, satu baris penjelas; panah bergeser saat disentuh. */
function Shortcut({
  href,
  title,
  text,
  icon,
}: {
  href: string;
  title: string;
  text: string;
  icon: string;
}) {
  return (
    <Link href={href} className="warga-tile">
      <span className="warga-tile-icon" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d={icon} />
        </svg>
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-bold text-ink">{title}</span>
        <span className="block text-xs text-ink-muted">{text}</span>
      </span>
      <span className="warga-tile-arrow" aria-hidden="true">
        →
      </span>
    </Link>
  );
}
