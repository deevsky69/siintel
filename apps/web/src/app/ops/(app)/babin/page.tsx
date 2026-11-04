import { getBabinList } from "@/lib/babin";
import { getProfile } from "@/lib/decisions";
import { getPublicSummary } from "@/lib/warga";
import { BabinTable } from "./babin-table";

export const dynamic = "force-dynamic";

/**
 * Kontak Babinkamtibmas per kelurahan — tabel CRUD (4 November 2026).
 *
 * Nomor dinas dan tautan grup tampil ke warga di peta dan bot; nomor WhatsApp Babin dan
 * chat id grup Telegram hanya tujuan buletin. Keterangan itu ada pada label isian di panel
 * samping, bukan sebagai paragraf di atas tabel.
 */
export default async function BabinPage() {
  const [list, profile, summary] = await Promise.all([
    getBabinList(),
    getProfile(),
    getPublicSummary().catch(() => null),
  ]);
  const canManage = profile.permissions.includes("babin:manage");
  const areas = (summary?.areas ?? []).map((area) => ({
    kelurahan: area.kelurahan,
    kecamatan: area.kecamatan,
    polsek: area.polsek ?? "—",
  }));
  return <BabinTable areas={areas} rows={list.data} canManage={canManage} />;
}
