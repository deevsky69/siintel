import Link from "next/link";
import { LevelBadge, Stars } from "@/components/warga/bits";
import { getPublicReviews, getPublicSummary } from "@/lib/warga";
import { ReviewForm } from "./review-form";

export const metadata = { title: "Survey Rasa Aman — SIGAP WARGA" };
export const dynamic = "force-dynamic";

const PROTECTIONS = [
  ["01", "Tanpa nama", "Tidak ada data identitas yang diminta."],
  ["02", "Diperiksa sebelum tayang", "Ulasan diperiksa moderator sebelum tayang."],
  [
    "03",
    "Persepsi, bukan angka kejadian",
    "Nilai rasa aman ditampilkan terpisah dari data laporan.",
  ],
] as const;

/**
 * Survey Rasa Aman — ulasan warga per kelurahan (mockup 10 November 2026).
 *
 * Spanduk merah mengingatkan bahwa ini bukan saluran pelaporan; lalu pilih kelurahan,
 * kartu navy berisi nilai rata-rata, ulasan yang tayang, formulir, daftar kelurahan yang
 * sudah diulas, dan kartu "Perlindungan data Anda". Anonim; tayang setelah moderasi.
 */
export default async function SurveyPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.kelurahan;
  const wanted = (Array.isArray(raw) ? raw[0] : raw) ?? "";
  const summary = await getPublicSummary().catch(() => null);
  if (!summary) {
    return (
      <div className="warga-wrap py-10">
        <p className="warga-card p-6 text-sm text-ink-muted">
          Survey belum dapat dimuat. Coba lagi sebentar.
        </p>
      </div>
    );
  }
  const area = summary.areas.find((row) => row.kelurahan.toLowerCase() === wanted.toLowerCase());
  const reviews = area ? await getPublicReviews(area.kelurahan).catch(() => null) : null;
  const byKecamatan = new Map<string, typeof summary.areas>();
  for (const row of summary.areas) {
    byKecamatan.set(row.kecamatan, [...(byKecamatan.get(row.kecamatan) ?? []), row]);
  }
  const reviewed = summary.areas
    .filter((row) => row.rating_count > 0)
    .sort((a, b) => b.rating_count - a.rating_count);

  return (
    <div>
      <div className="warga-banner">
        <div className="warga-wrap flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-3.5">
          <span className="text-[15px] font-semibold">
            Survey ini bukan saluran pelaporan. Untuk melaporkan kejadian, gunakan menu{" "}
            <Link href="/lapor">Lapor</Link> atau hubungi 110.
          </span>
          <a href="tel:110" className="warga-btn warga-btn-sm">
            Telepon 110 sekarang
          </a>
        </div>
      </div>

      <section className="warga-wrap pb-6 pt-12">
        <p className="warga-eyebrow">Survey Rasa Aman</p>
        <h1 className="mt-2 text-4xl text-[rgb(var(--warga-navy))] sm:text-[44px]">
          Seberapa aman kelurahan Anda?
        </h1>
        <p className="mt-3 max-w-[720px] text-[17px] leading-relaxed text-ink-faint">
          Nilai dan ulasan warga, anonim, per kelurahan. Ini persepsi, bukan angka kejadian;
          keduanya ditampilkan berdampingan di peta.
        </p>
      </section>

      <section className="warga-wrap flex flex-col gap-6 pb-16 pt-4">
        <form
          method="get"
          action="/survey"
          className="warga-card flex flex-wrap items-end gap-3.5 px-6 py-6 sm:px-8"
        >
          <label className="flex min-w-0 flex-[1_1_320px] flex-col gap-1.5">
            <span className="warga-label">Kelurahan</span>
            <select name="kelurahan" defaultValue={area?.kelurahan ?? ""} className="warga-field">
              <option value="">Pilih kelurahan…</option>
              {[...byKecamatan.entries()].map(([kecamatan, rows]) => (
                <optgroup key={kecamatan} label={kecamatan}>
                  {rows.map((row) => (
                    <option key={row.kelurahan} value={row.kelurahan}>
                      {row.kelurahan}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <button type="submit" className="warga-btn warga-btn-primary px-7">
            Lihat
          </button>
        </form>

        {area ? (
          <>
            <div className="warga-card-navy flex flex-wrap items-center justify-between gap-x-8 gap-y-5 px-6 py-6 sm:px-8">
              <div className="min-w-0">
                <p className="text-xs text-[rgb(var(--warga-soft))]">{area.kecamatan}</p>
                <h2 className="mt-0.5 text-2xl uppercase tracking-wide text-white">
                  Kelurahan {area.kelurahan}
                </h2>
                <div className="mt-2">
                  <LevelBadge level={area.level} />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-[40px] font-extrabold leading-none">
                  {reviews?.average ?? "–"}
                </span>
                <div>
                  <Stars value={reviews?.average ?? null} size="text-xl" />
                  <p className="mt-0.5 text-xs text-[rgb(var(--warga-soft))]">
                    {reviews && reviews.count > 0
                      ? `${reviews.count} ulasan tayang`
                      : "belum ada ulasan"}
                  </p>
                </div>
              </div>
              <Link
                href={`/peta?kecamatan=${encodeURIComponent(area.kecamatan)}&kelurahan=${encodeURIComponent(area.kelurahan)}`}
                className="warga-btn warga-btn-sm warga-btn-white-outline"
              >
                Lihat di peta →
              </Link>
            </div>

            <section className="warga-card px-6 py-6 sm:px-8" aria-labelledby="tayang">
              <h2 id="tayang" className="mb-3 text-lg text-[rgb(var(--warga-navy))]">
                Ulasan yang tayang
              </h2>
              {reviews && reviews.data.length > 0 ? (
                <ul className="flex flex-col gap-2.5">
                  {reviews.data.map((row) => (
                    <li
                      key={row.code}
                      className="border-l-[3px] border-[rgb(var(--warga-gold))] bg-base-950 px-3.5 py-3"
                    >
                      <div className="flex items-center gap-2.5 text-xs text-ink-faint">
                        <Stars value={row.rating} size="text-sm" />
                        <span>
                          {new Date(row.submitted_at).toLocaleDateString("id-ID", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })}
                        </span>
                      </div>
                      {row.comment ? (
                        <p className="mt-1.5 text-sm leading-relaxed text-ink">{row.comment}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="warga-empty">Belum ada ulasan yang tayang untuk kelurahan ini.</p>
              )}
            </section>

            <section className="warga-card p-6 sm:p-8">
              <ReviewForm kecamatan={area.kecamatan} kelurahan={area.kelurahan} />
            </section>
          </>
        ) : null}

        <section className="warga-card px-6 py-6 sm:px-8" aria-labelledby="diulas">
          <h2 id="diulas" className="mb-3 text-lg text-[rgb(var(--warga-navy))]">
            Kelurahan yang sudah diulas
          </h2>
          {reviewed.length > 0 ? (
            <ul className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {reviewed.map((row) => (
                <li key={row.kelurahan}>
                  <Link
                    href={`/survey?kelurahan=${encodeURIComponent(row.kelurahan)}`}
                    className="flex min-h-[52px] items-center justify-between gap-2.5 border-[1.5px] border-base-700 px-3.5 py-2 text-left transition-colors hover:border-accent-soft"
                  >
                    <span>
                      <span className="block font-semibold text-[rgb(var(--warga-navy))]">
                        {row.kelurahan}
                      </span>
                      <span className="block text-xs text-ink-faint">{row.kecamatan}</span>
                    </span>
                    <span className="whitespace-nowrap font-bold text-[rgb(var(--warga-gold))]">
                      {row.rating} ★{" "}
                      <span className="text-xs font-medium text-ink-faint">
                        ({row.rating_count})
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="warga-empty">
              Belum ada ulasan. Pilih kelurahan Anda di atas untuk memulai.
            </p>
          )}
        </section>

        <section className="warga-card-navy flex flex-col gap-4 p-7" aria-labelledby="lindung">
          <h2 id="lindung" className="text-xl text-white">
            Perlindungan data Anda
          </h2>
          <div className="grid gap-5 sm:grid-cols-3">
            {PROTECTIONS.map(([no, title, text]) => (
              <div key={no} className="flex gap-3.5">
                <span className="inline-flex h-9 w-9 flex-none items-center justify-center bg-[rgb(var(--warga-navy2))] text-[15px] font-medium text-[rgb(var(--warga-goldl))]">
                  {no}
                </span>
                <div>
                  <p className="font-bold text-white">{title}</p>
                  <p className="text-sm leading-relaxed text-[rgb(var(--warga-soft))]">{text}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </div>
  );
}
