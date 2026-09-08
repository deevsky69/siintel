import type { ReactNode } from "react";

/**
 * Penanda status data yang belum final.
 *
 * Dipakai bersama oleh Warning Center dan Evaluation Center. Keduanya menampilkan angka
 * yang **belum berstatus final** — ambang peringatan berstatus DEMO/PROPOSED (CLAUDE.md §11)
 * dan aturan pencocokan evaluasi belum ditetapkan (U-03, §26). Penanda ini sengaja
 * diletakkan di atas angka, bukan sebagai catatan kaki, supaya tidak terlewat pembaca.
 */
export function StatusNotice({
  status,
  tone = "accent",
  children,
}: {
  /** Status apa adanya dari API atau konfigurasi, mis. `PROPOSED`, `DEMO / PROPOSED`. */
  status: string;
  tone?: "accent" | "caution";
  children: ReactNode;
}) {
  const palette =
    tone === "caution"
      ? {
          box: "border-risk-high/40 bg-risk-high/10",
          badge: "bg-risk-high/20 text-risk-high",
          text: "text-risk-high",
        }
      : {
          box: "border-accent/25 bg-accent/5",
          badge: "bg-accent/15 text-accent",
          text: "text-accent-soft",
        };

  return (
    <div className={`flex flex-wrap items-start gap-3 rounded border px-3 py-2.5 ${palette.box}`}>
      <span className={`badge shrink-0 ${palette.badge}`}>{status}</span>
      <p className={`flex-1 text-xs leading-relaxed ${palette.text}`}>{children}</p>
    </div>
  );
}
