import Link from "next/link";
import type { NotificationFeed } from "@/lib/notifications";

/**
 * Spanduk merah di atas setiap halaman selama ada permintaan bantuan darurat yang belum
 * diterima. Inilah "pemberitahuan" bagi Administrator, Polsek, dan Pimpinan di web; ia
 * dihitung dari antrean yang sama dengan lonceng, jadi hilang begitu diterima.
 */
export function PanicBanner({ feed }: { feed: NotificationFeed | null }) {
  const group = feed?.groups.find((item) => item.kind === "PANIC");
  if (!group || group.total === 0) return null;
  const first = group.items[0];
  return (
    <Link
      href="/panic"
      className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded border border-risk-critical bg-risk-critical/15 px-3.5 py-2.5 text-sm text-ink transition hover:bg-risk-critical/25"
      role="alert"
    >
      <span className="badge bg-risk-critical text-base-950">DARURAT</span>
      <span className="font-heading font-semibold">
        {group.total} permintaan bantuan belum diterima
      </span>
      {first ? (
        <span className="text-xs text-ink-muted">
          {first.headline} · {first.detail}
        </span>
      ) : null}
      <span className="ml-auto text-xs uppercase tracking-wider text-risk-critical">Buka →</span>
    </Link>
  );
}
