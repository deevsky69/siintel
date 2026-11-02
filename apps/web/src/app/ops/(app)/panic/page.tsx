import { Basis } from "@/components/basis";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getProfile } from "@/lib/dashboard";
import { getPanicEvents, mapLink, PANIC_STATUS_LABELS, type PanicRow } from "@/lib/panic";
import { formatWib } from "@/lib/warnings";
import { PanicActions } from "./panic-actions";

export const dynamic = "force-dynamic";

/**
 * Panic Button — antrean permintaan bantuan darurat dari aplikasi warga.
 *
 * Sampai 8 Oktober 2026 layar ini sengaja bukan kanal sungguhan (yang kurang adalah
 * komitmen respons, bukan teknik). Pemilik proyek kemudian menetapkan penerimanya —
 * Administrator, Polsek wilayah itu, Pimpinan — dan kanalnya dibangun. Yang masih
 * PROPOSED: waktu tanggap dan eskalasi bila tidak ada yang menerima; karena itu 110
 * tetap disebut sebagai jalur resmi pada layar warga.
 */
export default async function PanicPage() {
  const [page, profile] = await Promise.all([getPanicEvents(), getProfile()]);
  const canAct = profile.permissions.includes("panic:acknowledge");
  const open = page.data.filter((row) => row.status === "OPEN");
  const handling = page.data.filter((row) => row.status === "ACKNOWLEDGED");
  const closed = page.data.filter((row) => row.status === "CLOSED").slice(0, 20);

  return (
    <div className="space-y-3">
      <div
        className={`rounded border px-3.5 py-3 ${
          open.length > 0
            ? "border-risk-critical/60 bg-risk-critical/10"
            : "border-base-800 bg-base-900/60"
        }`}
      >
        <p className={`stat-label ${open.length > 0 ? "text-risk-critical" : ""}`}>
          {open.length > 0
            ? `${open.length} permintaan bantuan belum diterima`
            : "Tidak ada permintaan bantuan yang belum diterima"}
        </p>
        <p className="mt-1 text-xs leading-relaxed text-ink-muted">
          Ditekan dari aplikasi warga, tanpa identitas. Untuk keadaan mengancam jiwa, jalur resmi
          tetap <strong className="text-ink">110</strong>.
        </p>
      </div>

      <Group title="Belum Diterima" rows={open} canAct={canAct} empty="Tidak ada." alarm />
      <Group title="Sedang Ditangani" rows={handling} canAct={canAct} empty="Tidak ada." />
      <Group title="Selesai (20 terakhir)" rows={closed} canAct={false} empty="Belum ada." />

      <Basis>{page.basis}</Basis>
    </div>
  );
}

function Group({
  title,
  rows,
  canAct,
  empty,
  alarm = false,
}: {
  title: string;
  rows: PanicRow[];
  canAct: boolean;
  empty: string;
  alarm?: boolean;
}) {
  return (
    <Panel title={title} action={<span className="panel-action">{rows.length}</span>}>
      {rows.length === 0 ? (
        <EmptyState label={empty} />
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li
              key={row.code}
              className={`rounded border p-3 ${alarm ? "border-risk-critical/40 bg-risk-critical/5" : "border-base-800"}`}
            >
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-sm font-bold text-ink">{row.code}</span>
                <span className="text-xs text-ink">
                  {row.kelurahan ? `${row.kelurahan}, ${row.kecamatan}` : "Lokasi tidak dikirim"}
                </span>
                <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs text-ink-muted">
                  {PANIC_STATUS_LABELS[row.status] ?? row.status}
                </span>
                <span className="ml-auto text-2xs text-ink-faint">{formatWib(row.pressed_at)}</span>
              </div>
              {row.note ? <p className="mt-1 text-xs text-ink-muted">{row.note}</p> : null}
              <p className="mt-1 text-2xs text-ink-faint">
                {mapLink(row) ? (
                  <a
                    href={mapLink(row) ?? "#"}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent hover:underline"
                  >
                    Buka titik di peta
                    {row.accuracy_m !== null ? ` (±${Math.round(row.accuracy_m)} m)` : ""}
                  </a>
                ) : (
                  "Tanpa titik peranti."
                )}
                {row.acknowledged_by
                  ? ` · diterima ${row.acknowledged_by} ${formatWib(row.acknowledged_at ?? "")}`
                  : ""}
                {row.closed_by
                  ? ` · ditutup ${row.closed_by}${row.closing_note ? `: ${row.closing_note}` : ""}`
                  : ""}
              </p>
              {canAct ? <PanicActions code={row.code} status={row.status} /> : null}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
