import Link from "next/link";
import { LevelBadge, Stars } from "@/components/warga/bits";
import { MapCanvas } from "@/components/warga/map-canvas";
import { Reveal } from "@/components/warga/reveal";
import { getPublicSummary, highlightAreas, longMonth } from "@/lib/warga";
import { getImbauanPublik } from "./lapor/actions";

export const metadata = { title: "SIGAP WARGA — Polres Metro Jakarta Selatan" };
export const dynamic = "force-dynamic";

const SERVICES = [
  {
    href: "/lacak",
    title: "Lacak laporan",
    text: "Masukkan nomor LP dan PIN pelapor untuk mengetahui tahap penanganan laporan.",
    cta: "Lacak sekarang →",
  },
  {
    href: "/lacak?tab=kendaraan",
    title: "Cek kendaraan bekas",
    text: "Periksa apakah nomor plat atau nomor rangka tercatat dalam laporan kehilangan.",
    cta: "Cek kendaraan →",
  },
  {
    href: "/survey",
    title: "Survey Rasa Aman",
    text: "Berikan penilaian rasa aman kelurahan Anda dengan skala 1–5 dan ulasan tanpa identitas.",
    cta: "Beri penilaian →",
  },
  {
    href: "/peta",
    title: "Peta kelurahan",
    text: "Data bulanan tiga jenis kejahatan serta kontak Babinkamtibmas setiap kelurahan.",
    cta: "Buka peta →",
  },
] as const;

/**
 * Beranda SIGAP WARGA (mockup 10 November 2026).
 *
 * Hero navy berisi peta kecamatan dan angka ringkas; strip Imbauan Polres; empat kartu
 * layanan; lalu dua kolom — daftar kelurahan berkerawanan tinggi dan kartu navy Survey Rasa
 * Aman. Yang tampil: imbauan yang sudah diterbitkan, tingkat kerawanan kasar per kecamatan,
 * dan sorotan survey. Tidak ada skor, prediksi, maupun titik kejadian: keputusan pemilik
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
    <div>
      <MapCanvas summary={summary} imbauan={imbauan} />

      <Reveal>
        <section className="warga-wrap pb-6 pt-16" aria-labelledby="layanan">
          <p className="warga-eyebrow">Layanan</p>
          <h2 id="layanan" className="mt-1.5 text-3xl text-[rgb(var(--warga-navy))] sm:text-[34px]">
            Layanan untuk warga
          </h2>
          <nav aria-label="Jalan pintas" className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {SERVICES.map((item) => (
              <Link key={item.href} href={item.href} className="warga-card-link">
                <span className="text-[19px] font-bold text-[rgb(var(--warga-navy))]">
                  {item.title}
                </span>
                <span className="text-[15px] leading-relaxed text-ink-faint">{item.text}</span>
                <span className="mt-auto text-sm font-bold text-accent-soft">{item.cta}</span>
              </Link>
            ))}
          </nav>
        </section>
      </Reveal>

      <Reveal delay={60}>
        <section className="warga-wrap flex flex-wrap items-stretch gap-6 pb-16 pt-6">
          <div className="warga-card min-w-0 flex-[3_1_520px] p-7">
            <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
              <div>
                <h2 className="text-2xl text-[rgb(var(--warga-navy))]">
                  Wilayah dengan kerawanan tinggi
                </h2>
                {summary ? (
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-faint">
                    {longMonth(summary.window_from)} – {longMonth(summary.window_to)} · pencurian
                    kendaraan, pencurian dengan pemberatan, pencurian dengan kekerasan
                  </p>
                ) : null}
              </div>
              <Link
                href="/peta"
                className="warga-link inline-flex min-h-[44px] items-center text-sm"
              >
                Lihat semua
              </Link>
            </div>
            {summary ? (
              highAreas.length > 0 ? (
                <ol className="warga-list mt-5">
                  {highAreas.map((area, index) => (
                    <li key={area.kelurahan}>
                      <Link
                        href={`/peta?kecamatan=${encodeURIComponent(area.kecamatan)}&kelurahan=${encodeURIComponent(area.kelurahan)}`}
                        className="warga-row"
                      >
                        <span className="warga-num">{index + 1}</span>
                        <span className="flex min-w-0 flex-1 flex-col">
                          <span className="truncate text-base font-bold text-[rgb(var(--warga-navy))]">
                            {area.kelurahan}
                          </span>
                          <span className="text-[13px] text-ink-faint">Kec. {area.kecamatan}</span>
                        </span>
                        <LevelBadge level={area.level} />
                        <span className="hidden whitespace-nowrap text-[13px] font-medium text-accent-soft sm:inline">
                          Lihat di peta →
                        </span>
                      </Link>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="warga-empty mt-5">
                  Tidak ada kelurahan bertingkat tinggi pada rentang ini.
                </p>
              )
            ) : (
              <p className="warga-empty mt-5">
                Ringkasan wilayah belum dapat dimuat. Coba lagi beberapa saat.
              </p>
            )}
            {summary ? (
              <p className="mt-4 text-[11px] leading-relaxed text-ink-faint">{summary.basis}</p>
            ) : null}
          </div>

          <section
            className="warga-card-navy flex min-w-0 flex-[2_1_340px] flex-col gap-4 p-7"
            aria-labelledby="survey"
          >
            <p className="warga-eyebrow !text-[rgb(var(--warga-goldl))]">Survey Rasa Aman</p>
            <h2 id="survey" className="text-[26px] text-white">
              Penilaian rasa aman lingkungan
            </h2>
            <p className="text-sm text-[rgb(var(--warga-soft))]">
              Ulasan warga per kelurahan, anonim, tayang setelah dimoderasi.
            </p>
            {highlights.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {highlights.map((area) => (
                  <li
                    key={area.kelurahan}
                    className="flex items-center gap-3 border-l-[3px] border-[rgb(var(--warga-gold))] bg-white px-3.5 py-3 text-ink"
                  >
                    <span className="inline-flex h-[22px] min-w-[28px] items-center justify-center bg-[rgb(var(--warga-navy))] px-1.5 text-xs font-bold text-[rgb(var(--warga-goldl))]">
                      {area.rating ?? "–"}/5
                    </span>
                    <span className="min-w-0 flex-1">
                      <Link
                        href={`/survey?kelurahan=${encodeURIComponent(area.kelurahan)}`}
                        className="block truncate text-sm font-bold text-[rgb(var(--warga-navy))]"
                      >
                        {area.kelurahan}
                      </Link>
                      <span className="text-xs text-ink-faint">Kec. {area.kecamatan}</span>
                    </span>
                    <Stars value={area.rating} size="text-sm" />
                    <span className="text-xs tabular-nums text-ink-faint">
                      ({area.rating_count})
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="border border-dashed border-white/30 p-4 text-sm text-[rgb(var(--warga-soft))]">
                Belum ada ulasan yang tayang. Jadilah yang pertama menilai kelurahan Anda.
              </p>
            )}
            <Link href="/survey" className="warga-btn warga-btn-gold mt-auto">
              Beri ulasan
            </Link>
          </section>
        </section>
      </Reveal>
    </div>
  );
}
