import { getPatternDna } from "@/lib/patterns";
import { resolveThreatType } from "./dna";
import { PatternDna } from "./pattern-dna";

export const dynamic = "force-dynamic";

/**
 * Halaman Crime Pattern DNA (TASK 094).
 *
 * Jenis gangguan terpilih hidup di alamat (`/pola?jenis=CURANMOR`), bukan di keadaan
 * komponen: profilnya diambil di server, halamannya tetap server component, dan tautan
 * satu jenis dapat disalin serta dibagikan saat paparan.
 *
 * Dua permintaan, bukan satu, dan itu disengaja. Permintaan pertama mengambil daftar
 * jenis yang ada di dalam **cakupan pengguna**; baru setelah itu isi alamat dicocokkan ke
 * daftar tersebut. Meneruskan isi alamat langsung ke backend akan membuat tautan usang
 * atau salah ketik berakhir sebagai galat 400 di tengah paparan — padahal jawaban yang
 * benar adalah membuka jenis dengan kejadian terbanyak dan menyatakan pilihannya.
 *
 * Seluruh angka berasal dari `GET /analytics/crime-pattern-dna`. Halaman ini tidak menghitung apa pun.
 */
export default async function PolaPage({
  searchParams,
}: {
  searchParams: Promise<{ jenis?: string | string[] }>;
}) {
  const params = await searchParams;
  const requested = typeof params.jenis === "string" ? params.jenis : null;

  const listing = await getPatternDna(null);
  const selected = resolveThreatType(listing.threat_types, requested);
  const detail = selected === null ? listing : await getPatternDna(selected);

  return (
    <PatternDna
      available={detail.threat_types}
      selected={detail.threat_type}
      profile={detail.profile}
      source={detail.source}
      scopeBasis={detail.scope_basis}
      analysisBasis={detail.analysis_basis}
    />
  );
}
