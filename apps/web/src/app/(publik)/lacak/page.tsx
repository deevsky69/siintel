import Link from "next/link";
import { TrackForm, VehicleForm } from "./forms";

export const metadata = { title: "Lacak Laporan — SIGAP WARGA" };

/**
 * Lacak laporan dan cek kendaraan (mockup 10 November 2026): hero navy berjudul "Lacak &
 * cek", kartu putih menumpang di tepinya dengan dua tab lebar, lalu dua kartu tautan
 * (buat laporan, hubungi 110). Keduanya hanya menjawab yang menjadi hak penanya.
 */
export default async function LacakPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const tab = params.tab === "kendaraan" ? "kendaraan" : "laporan";
  return (
    <div>
      <section className="warga-hero">
        <div className="mx-auto max-w-[960px] px-6 pb-24 pt-12 text-center">
          <h1 className="text-4xl text-white sm:text-[44px]">Lacak &amp; cek</h1>
          <p className="mx-auto mt-3 text-[17px] leading-relaxed text-[rgb(var(--warga-soft))]">
            Pantau tahap penanganan laporan Anda atau periksa kendaraan bekas sebelum membeli.
          </p>
        </div>
      </section>

      <section className="mx-auto -mt-16 max-w-[960px] px-4 pb-16 sm:px-6">
        <div className="warga-card-raised overflow-hidden">
          <div role="tablist" aria-label="Jenis pencarian" className="warga-tabs">
            <Link href="/lacak" role="tab" aria-selected={tab === "laporan"}>
              Lacak laporan
            </Link>
            <Link href="/lacak?tab=kendaraan" role="tab" aria-selected={tab === "kendaraan"}>
              Cek kendaraan
            </Link>
          </div>
          <div className="p-5 sm:p-8">{tab === "laporan" ? <TrackForm /> : <VehicleForm />}</div>
        </div>
        <div className="mt-5 flex flex-wrap gap-4">
          <Link
            href="/lapor"
            className="warga-card flex flex-[1_1_260px] items-center gap-3.5 px-5 py-4 text-[rgb(var(--warga-navy))]"
          >
            <span className="flex-1 font-bold">Belum memiliki laporan? Buat laporan kejadian</span>
            <span aria-hidden="true">→</span>
          </Link>
          <a
            href="tel:110"
            className="flex flex-[1_1_260px] items-center gap-3.5 bg-[#FEF2F2] px-5 py-4 text-[#7F1D1D]"
          >
            <span className="flex-1 font-bold">Kejadian sedang berlangsung? Hubungi 110</span>
            <span aria-hidden="true">→</span>
          </a>
        </div>
      </section>
    </div>
  );
}
