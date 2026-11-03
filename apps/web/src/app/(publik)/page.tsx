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
 * Susunan papan pengumuman: kanvas peta dengan panel keadaan wilayah (MapCanvas), lalu
 * grid bergaris berisi empat jalan pintas, lalu grid dua sel: Survey Rasa Aman dan wilayah
 * berkerawanan tinggi. Setiap bagian diawali kepala bergaris, seperti rubrik di koran.
 * Yang tampil: imbauan yang sudah diterbitkan, tingkat kerawanan kasar per kecamatan, dan
 * sorotan survey. Tidak ada skor, prediksi, maupun titik kejadian: keputusan pemilik
 * proyek, "sederhana saja untuk masyarakat".
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
    <div className="space-y-8">
      <MapCanvas summary={summary} imbauan={imbauan} />

      <Reveal>
        <section aria-labelledby="pintas">
          <h2 id="pintas" className="warga-rubric">
            Layanan
          </h2>
          <nav aria-label="Jalan pintas" className="warga-grid sm:grid-cols-2 lg:grid-cols-4">
            <Shortcut
              href="/lacak"
              title="Lacak laporan"
              text="Masukkan nomor LP dan PIN pelapor untuk melihat tahap penanganan."
            />
            <Shortcut
              href="/lacak?tab=kendaraan"
              title="Cek kendaraan bekas"
              text="Plat atau nomor rangka: tercatat dalam laporan atau tidak."
            />
            <Shortcut
              href="/survey"
              title="Survey Rasa Aman"
              text="Nilai kelurahanmu 1–5 dan tulis ulasan, tanpa nama."
            />
            <Shortcut
              href="/peta"
              title="Peta kelurahan"
              text="Angka per bulan, tiga jenis kejahatan, dan kontak Babinkamtibmas."
            />
          </nav>
        </section>
      </Reveal>

      <Reveal delay={60}>
        <div className="warga-grid md:grid-cols-2">
          <section className="warga-cell" aria-labelledby="survey">
            <div className="flex items-baseline justify-between gap-3">
              <h2 id="survey" className="warga-cell-title">
                Survey Rasa Aman
              </h2>
              <Link href="/survey" className="warga-link text-xs">
                Beri ulasan
              </Link>
            </div>
            <p className="mt-1 text-xs text-ink-muted">
              Ulasan warga per kelurahan, anonim, tayang setelah dimoderasi.
            </p>
            {highlights.length > 0 ? (
              <ul className="warga-list mt-4">
                {highlights.map((area) => (
                  <li key={area.kelurahan} className="flex items-center gap-3 py-2.5">
                    <div className="min-w-0 flex-1">
                      <Link
                        href={`/survey?kelurahan=${encodeURIComponent(area.kelurahan)}`}
                        className="warga-link block truncate text-sm font-semibold"
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
              <p className="warga-empty mt-4">
                Belum ada ulasan yang tayang. Jadilah yang pertama menilai kelurahan Anda.
              </p>
            )}
          </section>

          <section className="warga-cell" aria-labelledby="tinggi">
            <h2 id="tinggi" className="warga-cell-title">
              Wilayah dengan kerawanan tinggi
            </h2>
            {summary ? (
              <>
                <p className="mt-1 text-xs text-ink-muted">
                  {longMonth(summary.window_from)} – {longMonth(summary.window_to)} · pencurian
                  kendaraan, pencurian dengan pemberatan, dan dengan kekerasan.
                </p>
                {highAreas.length > 0 ? (
                  <ul className="warga-list mt-4">
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
                  <p className="warga-empty mt-4">
                    Tidak ada kelurahan bertingkat tinggi pada rentang ini.
                  </p>
                )}
                <p className="mt-4 text-[11px] leading-relaxed text-ink-faint">{summary.basis}</p>
              </>
            ) : (
              <p className="warga-empty mt-4">
                Ringkasan wilayah belum dapat dimuat. Coba lagi beberapa saat.
              </p>
            )}
          </section>
        </div>
      </Reveal>
    </div>
  );
}

/** Sel jalan pintas: judul, satu kalimat penjelas, panah berlingkar yang terisi saat disentuh. */
function Shortcut({ href, title, text }: { href: string; title: string; text: string }) {
  return (
    <Link href={href} className="warga-cell warga-tile">
      <span className="block text-base font-semibold leading-snug text-ink">{title}</span>
      <span className="mt-1.5 block text-sm leading-relaxed text-ink-muted">{text}</span>
      <span className="warga-tile-arrow" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </Link>
  );
}
