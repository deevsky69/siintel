import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getBabinList } from "@/lib/babin";
import { getProfile } from "@/lib/decisions";
import { getPublicSummary } from "@/lib/warga";
import { BabinForm } from "./babin-form";

export const dynamic = "force-dynamic";

/**
 * Kontak Babinkamtibmas per kelurahan (tahap 3). Nomor dinas tampil ke warga di peta dan
 * bot; nomor WhatsApp Babin dan chat id grup Telegram hanya tujuan buletin — tidak keluar.
 */
export default async function BabinPage() {
  const [list, profile, summary] = await Promise.all([
    getBabinList(),
    getProfile(),
    getPublicSummary().catch(() => null),
  ]);
  const canManage = profile.permissions.includes("babin:manage");
  const byKelurahan = new Map(list.data.map((row) => [row.kelurahan, row]));
  const areas = summary?.areas ?? [];
  return (
    <div className="space-y-3">
      <Panel
        title="Kontak Babinkamtibmas"
        action={
          <span className="panel-action">
            {list.total} dari {areas.length} kelurahan terisi
          </span>
        }
      >
        <p className="mb-3 text-2xs leading-relaxed text-ink-muted">
          Nomor yang ditampilkan ke warga adalah nomor dinas. Kolom WhatsApp Babin dan chat id grup
          Telegram dipakai bot untuk mengirim buletin mingguan; keduanya tidak pernah tampil ke
          warga. Baris dummy berlabel; data dummy ditanam lewat{" "}
          <span className="font-mono">scripts/isi-perkara-dummy-produksi.sh</span>.
        </p>
        {areas.length === 0 ? (
          <EmptyState label="Master kelurahan belum dapat dimuat." />
        ) : (
          <ul className="divide-y divide-base-800">
            {areas.map((area) => {
              const row = byKelurahan.get(area.kelurahan) ?? null;
              return (
                <li key={area.kelurahan} className="py-2.5">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
                    <span className="font-heading font-semibold text-ink">{area.kelurahan}</span>
                    <span className="text-ink-faint">
                      {area.kecamatan} · Polsek {area.polsek}
                    </span>
                    {row ? (
                      <>
                        <span className="text-ink">
                          {row.rank ? `${row.rank} ` : ""}
                          {row.name}
                        </span>
                        <span className="font-mono text-ink-muted">{row.phone_display}</span>
                        {row.telegram_chat_id ? (
                          <span className="text-2xs text-accent">grup Telegram</span>
                        ) : null}
                        {row.whatsapp_number ? (
                          <span className="text-2xs text-accent">WA Babin</span>
                        ) : null}
                        {row.is_dummy ? (
                          <span className="rounded bg-risk-moderate/20 px-1.5 py-0.5 text-2xs font-bold uppercase text-risk-moderate">
                            Dummy
                          </span>
                        ) : null}
                      </>
                    ) : (
                      <span className="text-ink-faint">belum terisi</span>
                    )}
                    {canManage ? <BabinForm row={row} kelurahan={area.kelurahan} /> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
}
