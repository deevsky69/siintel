import { getDailyBrief } from "@/lib/brief";
import { BriefDocument } from "./brief-document";

export const dynamic = "force-dynamic";

/**
 * Executive Brief harian (modul MVP #14).
 *
 * Satu-satunya keluaran yang ditujukan langsung kepada pimpinan — disebut spesifikasi
 * pada §3, §8 keluaran no. 8, dan §9 MVP no. 14. Bentuknya dokumen yang dapat dibaca dan
 * dibacakan, bukan dasbor angka kedua.
 *
 * Halaman ini hanya mengambil data; seluruh penyajian berada di `BriefDocument` supaya
 * dapat diuji tanpa backend.
 */
export default async function ExecutiveBriefPage() {
  const brief = await getDailyBrief();

  return <BriefDocument brief={brief} />;
}
