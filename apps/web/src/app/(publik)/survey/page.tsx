import Link from "next/link";
import { LevelBadge, Stars } from "@/components/warga/bits";
import { getPublicReviews, getPublicSummary } from "@/lib/warga";
import { ReviewForm } from "./review-form";

export const metadata = { title: "Survey Rasa Aman — SIGAP WARGA" };
export const dynamic = "force-dynamic";

/**
 * Survey Rasa Aman — ulasan warga per kelurahan (2 November 2026).
 *
 * Seperti ulasan tempat: pilih kelurahan, lihat nilai dan ulasan yang tayang, beri ulasan
 * sendiri. Anonim; tayang setelah moderasi (keputusan pemilik proyek).
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
      <p className="warga-card p-6 text-sm text-ink-muted">
        Survey belum dapat dimuat. Coba lagi sebentar.
      </p>
    );
  }
  const area = summary.areas.find((row) => row.kelurahan.toLowerCase() === wanted.toLowerCase());
  const reviews = area ? await getPublicReviews(area.kelurahan).catch(() => null) : null;
  const byKecamatan = new Map<string, typeof summary.areas>();
  for (const row of summary.areas) {
    byKecamatan.set(row.kecamatan, [...(byKecamatan.get(row.kecamatan) ?? []), row]);
  }

  return (
    <div className="space-y-4">
      <section className="warga-card p-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent-soft">
          Survey Rasa Aman
        </p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Seberapa aman kelurahan Anda?</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Nilai dan ulasan warga, anonim, per kelurahan. Ini persepsi, bukan angka kejadian —
          keduanya ditampilkan berdampingan di peta.
        </p>
        <form method="get" action="/survey" className="mt-4 flex flex-col gap-2 sm:flex-row">
          <select
            name="kelurahan"
            defaultValue={area?.kelurahan ?? ""}
            className="flex-1 rounded-full border border-base-800 bg-base-900 px-4 py-2.5 text-sm text-ink focus:border-accent focus:outline-none"
          >
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
          <button type="submit" className="warga-btn warga-btn-primary">
            Lihat
          </button>
        </form>
      </section>

      {area ? (
        <div className="grid gap-4 md:grid-cols-5">
          <section className="warga-card p-5 md:col-span-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs text-ink-faint">{area.kecamatan}</p>
                <h2 className="text-xl font-bold text-ink">Kelurahan {area.kelurahan}</h2>
              </div>
              <LevelBadge level={area.level} />
            </div>
            <div className="mt-3 flex items-center gap-3">
              <span className="text-4xl font-bold tabular-nums text-ink">
                {reviews?.average ?? "–"}
              </span>
              <div>
                <Stars value={reviews?.average ?? null} />
                <p className="text-xs text-ink-muted">
                  {reviews && reviews.count > 0
                    ? `${reviews.count} ulasan tayang`
                    : "belum ada ulasan"}
                </p>
              </div>
              <Link
                href={`/peta?kecamatan=${encodeURIComponent(area.kecamatan)}&kelurahan=${encodeURIComponent(area.kelurahan)}`}
                className="ml-auto text-xs font-semibold text-accent-soft"
              >
                Lihat di peta →
              </Link>
            </div>
            {reviews && reviews.data.length > 0 ? (
              <ul className="mt-4 divide-y divide-base-800">
                {reviews.data.map((row) => (
                  <li key={row.code} className="py-3">
                    <div className="flex items-center gap-2">
                      <Stars value={row.rating} size="text-sm" />
                      <span className="text-xs text-ink-faint">
                        {new Date(row.submitted_at).toLocaleDateString("id-ID", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                    {row.comment ? (
                      <p className="mt-1 text-sm leading-relaxed text-ink">{row.comment}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-ink-muted">
                Belum ada ulasan yang tayang untuk kelurahan ini.
              </p>
            )}
          </section>
          <section className="warga-card p-5 md:col-span-2">
            <ReviewForm kecamatan={area.kecamatan} kelurahan={area.kelurahan} />
          </section>
        </div>
      ) : (
        <section className="warga-card p-5">
          <h2 className="text-base font-bold text-ink">Kelurahan yang sudah diulas</h2>
          {summary.areas.some((row) => row.rating_count > 0) ? (
            <ul className="mt-3 divide-y divide-base-800">
              {summary.areas
                .filter((row) => row.rating_count > 0)
                .sort((a, b) => b.rating_count - a.rating_count)
                .map((row) => (
                  <li key={row.kelurahan}>
                    <Link
                      href={`/survey?kelurahan=${encodeURIComponent(row.kelurahan)}`}
                      className="flex items-center justify-between py-2.5"
                    >
                      <span>
                        <span className="block text-sm font-semibold text-ink">
                          {row.kelurahan}
                        </span>
                        <span className="text-xs text-ink-faint">{row.kecamatan}</span>
                      </span>
                      <span className="flex items-center gap-2">
                        <Stars value={row.rating} size="text-sm" />
                        <span className="text-xs tabular-nums text-ink-muted">
                          ({row.rating_count})
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-ink-muted">
              Belum ada ulasan. Pilih kelurahan Anda di atas untuk memulai.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
