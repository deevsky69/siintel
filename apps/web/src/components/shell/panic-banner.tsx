import Link from "next/link";
import {
  type NotificationFeed,
  type NotificationGroup,
  urgentGroups,
} from "@/lib/notifications-shape";

/**
 * Spanduk berkedip di atas setiap halaman selama ada yang mendesak: permintaan bantuan
 * darurat yang belum diterima, dan laporan warga berkategori mendesak (tawuran, begal —
 * keputusan pemilik proyek 9 Oktober 2026) yang belum ditriase. Dihitung dari antrean yang
 * sama dengan lonceng, jadi hilang begitu dikerjakan. Hanya tampil bagi yang berwenang
 * mengerjakannya atau diputuskan ikut diberi tahu — itu ditentukan API, bukan di sini.
 */
export function PanicBanner({ feed }: { feed: NotificationFeed | null }) {
  const groups = urgentGroups(feed);
  if (groups.length === 0) return null;
  return (
    <div className="mb-3 space-y-2">
      {groups.map((group) => (
        <UrgentRow key={group.kind} group={group} />
      ))}
    </div>
  );
}

function UrgentRow({ group }: { group: NotificationGroup }) {
  const panic = group.kind === "PANIC";
  const count = group.urgent_total ?? group.total;
  const sample = group.items.find((item) => panic || item.urgent) ?? group.items[0];
  return (
    <Link
      href={group.href}
      className="urgent-blink flex flex-wrap items-center gap-x-3 gap-y-1 rounded border border-risk-critical px-3.5 py-2.5 text-sm text-ink transition"
      role="alert"
    >
      <span className="badge bg-risk-critical text-base-950">{panic ? "DARURAT" : "SEGERA"}</span>
      <span className="font-heading font-semibold">
        {panic
          ? `${count} permintaan bantuan belum diterima`
          : `${count} laporan tawuran/begal belum ditriase`}
      </span>
      {sample ? (
        <span className="text-xs text-ink-muted">
          {sample.headline} · {sample.detail}
        </span>
      ) : null}
      <span className="ml-auto text-xs uppercase tracking-wider text-risk-critical">Buka →</span>
    </Link>
  );
}
