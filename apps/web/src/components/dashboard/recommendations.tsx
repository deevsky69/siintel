import { Panel } from "@/components/panel";
import type { RecommendationRow } from "@/lib/dashboard";

const FUNCTION_LABEL: Record<string, string> = {
  SAMAPTA: "Samapta",
  BINMAS: "Binmas",
  INTELKAM: "Intelkam",
  RESKRIM: "Reskrim",
  LANTAS: "Lantas",
};

export function RecommendationPanel({
  rows,
  forWarning,
}: {
  rows: RecommendationRow[];
  forWarning: string | null;
}) {
  return (
    <Panel
      title="AI Recommendation"
      action={forWarning ? <span className="panel-action">untuk {forWarning}</span> : null}
    >
      {rows.length === 0 ? (
        <p className="text-sm text-ink-muted">Belum ada rekomendasi untuk peringatan ini.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li
              key={row.code}
              className="flex gap-3 rounded border border-base-800 bg-base-950/40 px-3 py-2"
            >
              <span className="w-16 shrink-0 pt-0.5 font-heading text-xs font-bold uppercase tracking-wider text-accent">
                {FUNCTION_LABEL[row.recommended_function] ?? row.recommended_function}
              </span>
              <span className="flex-1 text-xs leading-relaxed text-ink">
                {row.recommendation_text}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Rekomendasi adalah opsi, bukan perintah (CLAUDE.md §13). Dinyatakan di layar
          supaya tidak ada yang menafsirkannya sebagai instruksi otomatis. */}
      <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
        Rekomendasi bersifat usulan. Tindakan operasional hanya lahir setelah keputusan pejabat
        berwenang.
      </p>
    </Panel>
  );
}
