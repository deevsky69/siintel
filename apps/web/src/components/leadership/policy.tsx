import { Panel } from "@/components/panel";
import type { LeadershipBoard } from "@/lib/leadership";

/**
 * Rekomendasi kebijakan.
 *
 * Pemilik proyek merencanakan blok ini kelak dihasilkan AI. Sampai model itu ada, setiap
 * butir di sini **diturunkan dengan aturan** dari angka yang tampil di layar yang sama, dan
 * label sumbernya dinyatakan terbuka.
 *
 * Menampilkannya sebagai keluaran AI sekarang akan menjadi penjelasan fiktif (CLAUDE.md
 * §27) — dan justru pada blok inilah kebohongan itu paling mahal, karena inilah yang
 * dibaca sebagai saran tindakan.
 */
export function PolicyRecommendations({ policy }: { policy: LeadershipBoard["policy"] }) {
  return (
    <Panel
      title="Rekomendasi Kebijakan"
      action={
        <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs uppercase tracking-wider text-ink-faint">
          Diturunkan aturan
        </span>
      }
    >
      {policy.recommendations.length === 0 ? (
        <p className="text-xs text-ink-muted">
          Tidak ada rekomendasi yang dapat diturunkan dari data pada jendela ini. Blok ini sengaja
          dibiarkan kosong alih-alih diisi saran umum yang tidak bersandar pada apa pun.
        </p>
      ) : (
        <ol className="space-y-2.5">
          {policy.recommendations.map((row, index) => (
            <li key={row.action} className="flex gap-2.5">
              <span className="font-mono text-2xs text-ink-faint">{index + 1}</span>
              <div className="flex-1">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-xs text-ink">{row.action}</span>
                  <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs text-ink-muted">
                    {row.function}
                  </span>
                  {/* Label sumber sama dengan yang dipakai faktor dominan di peta: RULE
                      berarti aturan yang benar-benar dijalankan, bukan temuan model. */}
                  <span className="font-mono text-2xs text-ink-faint">{row.source}</span>
                </div>
                <p className="mt-0.5 text-2xs leading-relaxed text-ink-muted">{row.basis}</p>
              </div>
            </li>
          ))}
        </ol>
      )}

      <p className="mt-3 text-2xs leading-relaxed text-ink-faint">{policy.basis}</p>
    </Panel>
  );
}
