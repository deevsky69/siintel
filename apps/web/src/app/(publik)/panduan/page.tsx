import Link from "next/link";
import { getSecurityGuides } from "@/lib/warga";

export const metadata = { title: "Panduan Pengamanan — SIGAP BERSAMA" };
export const dynamic = "force-dynamic";

/**
 * Panduan pengamanan kos, parkir, gedung, dan lingkungan RT/RW (naskah Taskap 4.7 f), dan cara
 * berlangganan imbauan bulanan kelurahan (4.7 b). Teks panduan dari konfigurasi API; angka di
 * samping tiap panduan adalah agregat se-Polres setahun terakhir — tanpa alamat.
 */
export default async function PanduanPage() {
  const guides = await getSecurityGuides().catch(() => null);
  return (
    <div>
      <section className="warga-wrap pb-6 pt-12">
        <p className="warga-eyebrow">Panduan pengamanan</p>
        <h1 className="mt-2 text-4xl text-[rgb(var(--warga-navy))] sm:text-[44px]">
          Langkah yang bisa dikerjakan sendiri
        </h1>
        <p className="mt-3 max-w-[720px] text-[17px] leading-relaxed text-ink-faint">
          Untuk penghuni kos, pengendara, pengelola gedung, dan pengurus RT/RW. Disusun dari pola
          pencurian yang tercatat di wilayah Polres Metro Jakarta Selatan.
        </p>
      </section>

      <section className="warga-wrap flex flex-col gap-6 pb-16 pt-4">
        {guides === null ? (
          <p className="warga-card p-6 text-sm text-ink-muted">
            Panduan belum dapat dimuat. Coba lagi sebentar.
          </p>
        ) : guides.data.length === 0 ? (
          <p className="warga-empty">Belum ada panduan.</p>
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            {guides.data.map((guide) => (
              <article
                key={guide.id}
                id={guide.id}
                className="warga-card flex flex-col gap-4 px-6 py-6 sm:px-8"
              >
                <header>
                  <h2 className="text-xl text-[rgb(var(--warga-navy))]">{guide.title}</h2>
                  <p className="mt-1 text-sm text-ink-faint">Untuk: {guide.audience}</p>
                </header>
                <ol className="flex list-decimal flex-col gap-2 pl-5 text-[15px] leading-relaxed text-ink">
                  {guide.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                {guide.pattern.incidents > 0 ? (
                  <p className="mt-auto border-l-[3px] border-[rgb(var(--warga-gold))] bg-base-950 px-3.5 py-3 text-sm leading-relaxed text-ink-muted">
                    Setahun terakhir tercatat <b>{guide.pattern.incidents}</b> pencurian di jenis
                    tempat ini
                    {guide.pattern.share_pct === null
                      ? ""
                      : ` (${guide.pattern.share_pct}% dari seluruh kejadian)`}
                    {guide.pattern.peak_block
                      ? `, paling sering pukul ${guide.pattern.peak_block}`
                      : ""}
                    {guide.pattern.top_modus[0]
                      ? `. Cara terbanyak: ${guide.pattern.top_modus[0].modus.toLowerCase()}`
                      : ""}
                    .
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        )}

        <section
          id="langganan"
          className="warga-card-navy flex flex-col gap-4 p-7"
          aria-labelledby="langganan-judul"
        >
          <h2 id="langganan-judul" className="text-xl text-white">
            Imbauan bulanan untuk kelurahan Anda
          </h2>
          <p className="max-w-[720px] text-[15px] leading-relaxed text-[rgb(var(--warga-soft))]">
            Di percakapan WhatsApp atau Telegram SIGAP, ketik{" "}
            <b className="text-white">/langganan nama kelurahan</b> — misalnya{" "}
            <b className="text-white">/langganan Tebet Timur</b>. Setiap awal bulan Anda menerima
            jenis kejadian yang perlu diwaspadai, rentang jam rawannya, dan langkah pencegahannya.
          </p>
          <p className="max-w-[720px] text-sm leading-relaxed text-[rgb(var(--warga-soft))]">
            Yang disimpan hanya pengenal percakapan dan nama kelurahan — tanpa nama dan tanpa
            alamat. Ketik <b className="text-white">/berhenti</b> kapan saja; data langganan
            langsung dihapus.
          </p>
          <div>
            <Link href="/peta" className="warga-btn warga-btn-sm warga-btn-white-outline">
              Lihat situasi kelurahan Anda →
            </Link>
          </div>
        </section>

        {guides ? (
          <p className="text-xs leading-relaxed text-ink-faint">
            {guides.basis} {guides.closing}
          </p>
        ) : null}
      </section>
    </div>
  );
}
