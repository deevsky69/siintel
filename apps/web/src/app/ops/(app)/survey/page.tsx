import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getProfile } from "@/lib/decisions";
import { getModerationQueue } from "@/lib/reviews";
import { ModerationForm } from "./moderation-form";

export const dynamic = "force-dynamic";

const STATUSES = ["PENDING", "PUBLISHED", "REJECTED"] as const;
const LABEL: Record<(typeof STATUSES)[number], string> = {
  PENDING: "Menunggu",
  PUBLISHED: "Tayang",
  REJECTED: "Ditolak",
};

/**
 * Moderasi Survey Rasa Aman (2 November 2026). Ulasan warga anonim tayang hanya setelah
 * diputuskan di sini; nilai rata-rata di sisi warga dihitung dari yang tayang saja.
 */
export default async function SurveyModerationPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.status;
  const wanted = ((Array.isArray(raw) ? raw[0] : raw) ?? "PENDING").toUpperCase();
  const status = STATUSES.find((value) => value === wanted) ?? "PENDING";
  const [queue, profile] = await Promise.all([getModerationQueue(status), getProfile()]);
  const canModerate = profile.permissions.includes("review:moderate");

  return (
    <div className="space-y-3">
      <Panel
        title="Survey Rasa Aman — Moderasi"
        action={<span className="panel-action">{queue.pending_total} menunggu</span>}
      >
        <div className="mb-3 flex flex-wrap gap-2">
          {STATUSES.map((value) => (
            <Link
              key={value}
              href={`/ops/survey?status=${value}`}
              className={`rounded border px-2.5 py-1 text-xs ${
                value === status
                  ? "border-accent/60 bg-accent/10 text-accent"
                  : "border-base-700 text-ink-muted hover:text-ink"
              }`}
            >
              {LABEL[value]}
            </Link>
          ))}
          <a
            href="/ops/survey"
            target="_blank"
            rel="noreferrer"
            className="ml-auto text-xs text-ink-faint underline hover:text-ink-muted"
          >
            Lihat tampilan warga
          </a>
        </div>
        {queue.data.length === 0 ? (
          <EmptyState label={`Tidak ada ulasan berstatus ${LABEL[status].toLowerCase()}.`} />
        ) : (
          <ul className="divide-y divide-base-800">
            {queue.data.map((row) => (
              <li key={row.code} className="py-3">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
                  <span className="font-mono text-ink-faint">{row.code}</span>
                  <span className="font-heading font-semibold text-ink">
                    {row.kelurahan}, {row.kecamatan}
                  </span>
                  <span className="text-risk-moderate">{"★".repeat(row.rating)}</span>
                  <span className="text-ink-faint">
                    {new Date(row.submitted_at).toLocaleString("id-ID")}
                  </span>
                  {row.moderated_by ? (
                    <span className="text-ink-faint">
                      · {LABEL[row.status].toLowerCase()} oleh {row.moderated_by}
                      {row.moderation_note ? ` — ${row.moderation_note}` : ""}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 text-sm text-ink">
                  {row.comment ?? <span className="text-ink-faint">Tanpa komentar.</span>}
                </p>
                {canModerate && row.status === "PENDING" ? (
                  <ModerationForm code={row.code} />
                ) : null}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-faint">
          Tolak ulasan yang memuat identitas orang lain, tuduhan terhadap orang tertentu, kata
          kasar, atau iklan. Ulasan adalah persepsi warga, bukan data kejadian.
        </p>
      </Panel>
    </div>
  );
}
