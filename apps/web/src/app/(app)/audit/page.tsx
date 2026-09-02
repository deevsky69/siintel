import { getAuditLogs, getAuditSummary, readFilters } from "@/lib/audit";
import { AuditBoard } from "./audit-board";

export const dynamic = "force-dynamic";

/**
 * Penelusuran jejak audit (TASK 142).
 *
 * Ringkasan penolakan dibuka lebih dulu, bukan daftar keberhasilan: yang pertama dicari
 * saat memeriksa audit adalah percobaan yang ditolak. Audit yang hanya memuat `SUCCESS`
 * hanya membuktikan bahwa yang berhasil memang berhasil.
 */
export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const filters = readFilters(await searchParams);
  const [page, summary] = await Promise.all([getAuditLogs(filters), getAuditSummary(filters)]);

  return <AuditBoard page={page} summary={summary} filters={filters} />;
}
