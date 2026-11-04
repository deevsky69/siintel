"use client";

import { useState } from "react";
import { Drawer } from "@/components/drawer";
import { Attachments } from "@/components/reports/attachments";
import { areaOf, type CitizenReportRow, formatMoment } from "@/lib/community-format";

/**
 * Rincian satu laporan masyarakat di panel samping (4 November 2026).
 *
 * Uraian, lokasi tertulis, waktu kejadian, dan lampiran dipindahkan dari baris tabel ke
 * sini supaya tabelnya dapat dipindai sekilas. Lampiran tetap tidak digambar sampai
 * petugas membukanya (komponen `Attachments`).
 */
export function ReportDetail({
  report,
  statusLabel,
}: {
  report: CitizenReportRow;
  statusLabel: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className="btn-sm" onClick={() => setOpen(true)}>
        Rincian
      </button>
      {open ? (
        <Drawer open onClose={() => setOpen(false)} title={report.code}>
          <dl className="space-y-3 text-xs">
            <Row label="Kategori">{report.category}</Row>
            <Row label="Tahapan">{statusLabel}</Row>
            <Row label="Masuk">{formatMoment(report.reported_at)}</Row>
            <Row label="Waktu kejadian">{formatMoment(report.incident_time)}</Row>
            <Row label="Wilayah">
              {areaOf(report)}
              {report.coordinate_source === "REPORTER_GPS" ? (
                <span className="ml-2 badge bg-accent/15 text-accent">titik pelapor</span>
              ) : null}
            </Row>
            {report.location_text ? (
              <Row label="Lokasi tertulis">{report.location_text}</Row>
            ) : null}
            <Row label="Uraian">
              <p className="whitespace-pre-wrap leading-relaxed text-ink">
                {report.description ?? <span className="text-ink-faint">tidak ada uraian</span>}
              </p>
            </Row>
            <Row label="Penilaian petugas">
              Urgensi {report.urgency_score ?? "—"} · Verifikasi {report.verification_score ?? "—"}
            </Row>
            {report.attachments > 0 ? (
              <Row label="Lampiran">
                <Attachments code={report.code} count={report.attachments} />
              </Row>
            ) : null}
          </dl>
        </Drawer>
      ) : null}
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="field-label">{label}</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  );
}
