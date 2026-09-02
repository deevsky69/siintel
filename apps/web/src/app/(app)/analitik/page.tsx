import Link from "next/link";
import { Panel } from "@/components/panel";
import { getSpatialPattern, getTimePattern, getTrend } from "@/lib/analytics";
import { AnalyticsView } from "./analytics-view";
import { analyticsHref, isReversedRange, readSelection } from "./display";

export const dynamic = "force-dynamic";

/**
 * Layar Crime Analytics (TASK 035).
 *
 * Menjawab yang diminta Resume Spesifikasi §3: analisis tren, distribusi jenis gangguan,
 * hari/jam rawan, dan perbandingan antarwilayah. Sudut pandangnya **perbandingan lintas
 * jenis dan lintas waktu**, berbeda dari `/pola` yang memprofilkan satu jenis menurut lima
 * dimensi — layar menyatakan bedanya di paling atas dan menautkan keduanya.
 *
 * Tiga permintaan dikirim serentak. Ketiganya berbagi penyaring tanggal; penyaring jenis
 * hanya berlaku bagi dua yang pertama, sebab jenis gangguan justru menjadi kolom
 * perbandingan antarwilayah.
 *
 * Penyaring hidup di alamat (`/analitik?jenis=CURANMOR&dari=2025-01-01`), bukan di keadaan
 * komponen: halaman tetap server component dan tautannya dapat dibagikan saat paparan.
 */
export default async function AnalyticsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const selection = readSelection(params);

  // Rentang terbalik dijawab dengan kalimat yang dapat ditindaklanjuti, bukan dengan layar
  // galat. Backend tetap menolaknya sendiri dengan 400 — ini bukan penggantinya.
  if (isReversedRange(selection)) {
    return (
      <Panel title="Crime Analytics">
        <div className="text-xs leading-relaxed text-ink-muted">
          <p>
            Rentang tanggalnya terbalik: tanggal awal ({selection.dateFrom}) melewati tanggal akhir
            ({selection.dateTo}), sehingga tidak ada rentang yang dapat dihitung.
          </p>
          <p className="mt-2">
            <Link
              href={analyticsHref(selection, { dateFrom: null, dateTo: null })}
              className="text-accent hover:text-accent-soft"
            >
              Lepas rentang tanggal dan tampilkan seluruh data →
            </Link>
          </p>
        </div>
      </Panel>
    );
  }

  const query = {
    threatType: selection.threatType,
    dateFrom: selection.dateFrom,
    dateTo: selection.dateTo,
  };
  const [trend, pattern, spatial] = await Promise.all([
    getTrend(query),
    getTimePattern(query),
    getSpatialPattern(query),
  ]);

  return <AnalyticsView selection={selection} trend={trend} pattern={pattern} spatial={spatial} />;
}
