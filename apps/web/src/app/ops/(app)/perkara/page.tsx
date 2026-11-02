import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getCaseFiles } from "@/lib/case-files";
import { getProfile } from "@/lib/decisions";
import { getPublicSummary } from "@/lib/warga";
import { NewCaseForm, StageForm } from "./case-forms";

export const dynamic = "force-dynamic";

/**
 * Berkas perkara 3C (tahap 2, 2 November 2026): yang dilacak warga lewat nomor LP + PIN dan
 * yang dicocokkan pada cek kendaraan. Baris DUMMY berlabel dan menampilkan PIN-nya supaya
 * dapat dicoba; perkara nyata hanya menampilkan PIN sekali saat dicatat.
 */
export default async function PerkaraPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return (Array.isArray(value) ? value[0] : value) ?? "";
  };
  const stage = one("tahap").toUpperCase();
  const q = one("cari");
  const [list, profile, summary] = await Promise.all([
    getCaseFiles(stage, q),
    getProfile(),
    getPublicSummary().catch(() => null),
  ]);
  const canWrite = profile.permissions.includes("case_file:write");
  const areas = new Map<string, string[]>();
  for (const area of summary?.areas ?? []) {
    areas.set(area.kecamatan, [...(areas.get(area.kecamatan) ?? []), area.kelurahan]);
  }
  const areaRows = [...areas.entries()].map(([kecamatan, kelurahan]) => ({ kecamatan, kelurahan }));

  return (
    <div className="space-y-3">
      <Panel
        title="Berkas Perkara 3C"
        action={<span className="panel-action">{list.total} perkara</span>}
      >
        <form
          method="get"
          action="/ops/perkara"
          className="mb-3 flex flex-wrap items-center gap-2 text-xs"
        >
          <select
            name="tahap"
            defaultValue={stage}
            className="rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink"
          >
            <option value="">Semua tahap</option>
            {list.stages.map((row) => (
              <option key={row.code} value={row.code}>
                {row.label}
              </option>
            ))}
          </select>
          <input
            name="cari"
            defaultValue={q}
            placeholder="Nomor LP atau plat"
            className="min-w-[200px] rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink"
          />
          <button
            type="submit"
            className="rounded border border-base-700 px-3 py-1 text-xs text-ink-muted hover:text-ink"
          >
            Saring
          </button>
          <a
            href="/lacak"
            target="_blank"
            rel="noreferrer"
            className="ml-auto text-xs text-ink-faint underline hover:text-ink-muted"
          >
            Lihat tampilan warga
          </a>
        </form>
        {list.data.length === 0 ? (
          <EmptyState label="Tidak ada berkas perkara pada saringan ini." />
        ) : (
          <ul className="divide-y divide-base-800">
            {list.data.map((row) => (
              <li key={row.lp_number} className="py-3">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
                  <span className="font-mono text-ink">{row.lp_number}</span>
                  <span className="font-heading font-semibold text-ink">{row.crime_type}</span>
                  <span className="text-ink-muted">
                    {row.kelurahan}, {row.kecamatan}
                  </span>
                  <span className="text-ink-faint">
                    {new Date(row.reported_on).toLocaleDateString("id-ID")}
                  </span>
                  <span className="rounded border border-accent/40 bg-accent/10 px-1.5 py-0.5 text-2xs text-accent">
                    {row.stage_label}
                  </span>
                  {row.is_dummy ? (
                    <span className="rounded bg-risk-moderate/20 px-1.5 py-0.5 text-2xs font-bold uppercase text-risk-moderate">
                      Dummy · PIN {row.dummy_pin}
                    </span>
                  ) : null}
                </div>
                {row.vehicle_plate ? (
                  <p className="mt-1 text-xs text-ink-muted">
                    Kendaraan <span className="font-mono text-ink">{row.vehicle_plate}</span>
                    {row.vehicle_desc ? ` · ${row.vehicle_desc}` : ""}
                    {row.vehicle_vin ? ` · rangka ${row.vehicle_vin}` : ""}
                    {row.vehicle_recovered ? (
                      <span className="ml-2 font-semibold text-risk-low">ditemukan</span>
                    ) : null}
                  </p>
                ) : null}
                {canWrite ? <StageForm row={row} stages={list.stages} /> : null}
              </li>
            ))}
          </ul>
        )}
      </Panel>
      {canWrite ? (
        <Panel title="Catat Perkara Baru">
          <NewCaseForm areas={areaRows} />
          <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-faint">
            PIN dibuat sistem dan hanya ditampilkan sekali; sampaikan kepada pelapor bersama nomor
            LP. Warga melacak di{" "}
            <Link href="/lacak" className="underline">
              /lacak
            </Link>
            . Data dummy produksi ditanam lewat{" "}
            <span className="font-mono">scripts/isi-perkara-dummy-produksi.sh</span>.
          </p>
        </Panel>
      ) : null}
    </div>
  );
}
