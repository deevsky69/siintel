import Link from "next/link";
import { Panel } from "@/components/panel";
import type { AreaStatus, AreaStatusRow, AttentionItem, Reports24h } from "@/lib/leadership";
import { AREA_STATUS_TONE, toneOf } from "@/lib/leadership";

/**
 * Empat kartu pembuka layar Pimpinan (permintaan pemilik proyek, 2 September 2026).
 *
 * Urutannya mengikuti urutan pertanyaan, bukan urutan ketersediaan data: apa yang masuk,
 * bagaimana keadaan wilayah, apa yang menuntut tindakan saya, dan di mana saya menaruh
 * sumber daya.
 */

function Card({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <Panel title={title} action={action} className="h-full">
      {children}
    </Panel>
  );
}

function Figure({ value, unit }: { value: number | string; unit?: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="font-heading text-4xl font-bold leading-none text-ink">{value}</span>
      {unit ? <span className="text-xs text-ink-muted">{unit}</span> : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex items-center justify-between border-t border-base-800 py-1 text-[11px]">
      <span className="text-ink-muted">{label}</span>
      <span className="font-mono text-ink">{value}</span>
    </div>
  );
}

export function ReportsCard({ reports }: { reports: Reports24h }) {
  return (
    <Card title="Laporan Masuk">
      <Figure value={reports.total} unit="laporan" />
      <p className="mt-1 text-[10px] text-ink-faint">24 jam terakhir</p>

      {/* Rincian tidak boleh disembunyikan di balik total: ketiganya berbeda asal dan
          berbeda keandalan, dan pembaca yang hanya melihat total akan menyimpulkan hal
          yang berbeda dari yang sebenarnya dihitung. */}
      <div className="mt-3">
        <Row label="Kejadian kriminal" value={reports.crime_incidents} />
        <Row label="Laporan intelijen" value={reports.intelligence_reports} />
        <Row label="Laporan masyarakat" value={reports.citizen_reports} />
      </div>

      {reports.citizen_reports_without_location > 0 ? (
        <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">
          {reports.citizen_reports_without_location} laporan masyarakat di antaranya tanpa lokasi
          yang cocok dengan master lokasi, sehingga tidak muncul di peta.
        </p>
      ) : null}

      <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">
        Laporan intelijen dicacah per hari ({reports.intelligence_date}) karena hanya bertanggal,
        tanpa jam.
      </p>
    </Card>
  );
}

export function AreaStatusCard({ areaStatus }: { areaStatus: AreaStatus }) {
  const dominant = areaStatus.tally.reduce(
    (best, row) => (row.areas > best.areas ? row : best),
    areaStatus.tally[0] ?? { status: "", label: "—", areas: 0 },
  );

  return (
    <Card
      title="Status Wilayah"
      action={
        <span className="text-[10px] uppercase tracking-wider text-ink-faint">
          {areaStatus.mapping_status}
        </span>
      }
    >
      {areaStatus.areas.length === 0 ? (
        <p className="text-xs text-ink-muted">Belum ada penilaian risiko untuk kewenangan Anda.</p>
      ) : (
        <>
          <div className="flex flex-wrap gap-1.5">
            {areaStatus.tally.map((row) => (
              <span
                key={row.status}
                className={`rounded border px-2 py-1 text-[11px] ${toneOf(
                  AREA_STATUS_TONE,
                  row.status,
                )}`}
              >
                {row.label} <span className="font-mono font-semibold">{row.areas}</span>
              </span>
            ))}
          </div>

          <p className="mt-3 text-xs leading-relaxed text-ink-muted">
            <strong className="text-ink">{dominant.areas}</strong> dari {areaStatus.areas.length}{" "}
            kecamatan berstatus {dominant.label} pada penilaian{" "}
            {areaStatus.assessment_date ?? "terakhir"}.
          </p>

          <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">
            Status mengikuti sel dengan skor tertinggi di kecamatan itu, sama seperti peta. Pemetaan
            empat kelas risiko ke tiga nama status masih{" "}
            <strong>{areaStatus.mapping_status}</strong> dan belum disetujui.
          </p>
        </>
      )}
    </Card>
  );
}

export function AttentionCard({ items }: { items: AttentionItem[] }) {
  const warnings = items.filter((item) => item.kind === "EARLY_WARNING").length;
  const decisions = items.filter((item) => item.kind === "RECOMMENDATION").length;

  return (
    <Card title="Perlu Perhatian Segera">
      {items.length === 0 ? (
        <p className="text-xs text-ink-muted">
          Tidak ada peringatan aktif, rekomendasi tertunda, maupun laporan yang belum diverifikasi.
        </p>
      ) : (
        <>
          <Figure value={items.length} unit="butir" />
          <p className="mt-1 text-[10px] text-ink-faint">
            {warnings} peringatan belum diterima · {decisions} menunggu keputusan Anda
          </p>

          <ul className="mt-3 space-y-1.5">
            {items.slice(0, 4).map((item) => (
              <li key={`${item.kind}-${item.code ?? item.headline}`}>
                <Link
                  href={item.href}
                  className="block rounded border border-base-800 px-2 py-1.5 transition-colors hover:border-accent/40"
                >
                  <span className="block text-[11px] text-ink">{item.headline}</span>
                  <span className="block text-[10px] text-ink-faint">
                    {item.kecamatan ?? "lintas wilayah"} · {item.why}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}

export function PriorityAreasCard({ areas }: { areas: AreaStatusRow[] }) {
  return (
    <Card title="Wilayah Prioritas">
      {areas.length === 0 ? (
        <p className="text-xs text-ink-muted">Belum ada penilaian risiko untuk kewenangan Anda.</p>
      ) : (
        <ol className="space-y-2">
          {areas.map((area, index) => (
            <li key={area.kecamatan} className="flex items-center gap-2.5">
              <span className="font-mono text-[10px] text-ink-faint">{index + 1}</span>
              <Link
                href={`/peta?wilayah=${encodeURIComponent(area.kecamatan)}`}
                className="flex-1 text-xs text-ink hover:text-accent"
              >
                {area.kecamatan}
              </Link>
              <span
                className={`rounded border px-1.5 py-0.5 text-[10px] ${toneOf(
                  AREA_STATUS_TONE,
                  area.status,
                )}`}
              >
                {area.label}
              </span>
              <span className="w-14 text-right font-mono text-xs text-ink">
                {area.risk_score}
                <span className="text-ink-faint">/{area.average_risk_score}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
      <p className="mt-3 text-[10px] leading-relaxed text-ink-faint">
        Angka menunjukkan <span className="font-mono">sel tertinggi</span> /{" "}
        <span className="font-mono">rata-rata seluruh sel</span>. Keduanya menjawab pertanyaan yang
        berbeda: yang terburuk, dan keadaan menyeluruh.
      </p>
    </Card>
  );
}
