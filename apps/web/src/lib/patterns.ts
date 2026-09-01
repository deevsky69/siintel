import { apiGet } from "./api";

/**
 * Crime Pattern DNA (TASK 094).
 *
 * ```text
 * GET /analytics/crime-pattern-dna                        → daftar jenis gangguan + jumlahnya
 * GET /analytics/crime-pattern-dna?threat_type=CURANMOR   → profil lima dimensi satu jenis
 * ```
 *
 * Modul ini **hanya** menerjemahkan bentuk respons; tidak ada angka yang dihitung di sini.
 * Seluruh agregasi — jumlah, persentase, peringkat, pengulangan per grid — berasal dari
 * `apps/api/.../routers/patterns.py`, karena penentuan "apa yang dihitung sebagai pola"
 * adalah aturan analitik dan tempatnya di backend (CLAUDE.md §21, §23).
 *
 * Yang perlu diingat saat membaca layar ini:
 *
 * - **Ini bukan prediksi.** Isinya sebaran kejadian yang sudah terjadi. Respons tidak
 *   membawa skor risiko maupun tingkat keyakinan, dan layar tidak boleh menambahkannya.
 * - **Tidak ada nilai yang ditandai "signifikan".** Backend sengaja tidak menandai apa
 *   pun karena ambangnya belum ditetapkan; antarmuka tidak menambal itu dengan penandaan
 *   sendiri (CLAUDE.md §11).
 * - **`denominator` selalu ikut ditampilkan.** Persentase tanpa penyebut menyesatkan.
 *
 * Berkas ini memanggil `lib/api.ts`, yang membaca cookie sesi, sehingga hanya boleh
 * dipakai dari server. Pembantu tampilan murni ada di `app/(app)/pola/dna.ts`.
 */

/** Satu golongan di dalam sebuah distribusi. */
export type PatternBucket = {
  /** Nilai mentah dari database — dipakai sebagai kunci React, bukan untuk ditampilkan. */
  key: string;
  label: string;
  incidents: number;
  /** Persentase terhadap `denominator` distribusinya, bukan terhadap seluruh kejadian. */
  share_percent: number;
};

/**
 * Satu sebaran.
 *
 * `ordering` menyatakan urutan yang sudah ditetapkan backend dan **tidak boleh diurutkan
 * ulang di layar**: `rank` berarti terbanyak lebih dulu, `natural` berarti urut jam
 * (00–23) atau urut hari (Senin–Minggu). Mengurutkan sebaran jam menurut jumlah akan
 * menghilangkan justru hal yang membuatnya terbaca — bahwa jam rawan saling berdekatan.
 */
export type PatternDistribution = {
  id: string;
  label: string;
  ordering: "rank" | "natural";
  denominator: number;
  buckets: PatternBucket[];
};

/** Satu grid yang mengalami kejadian berulang untuk jenis ini. */
export type RepeatGrid = {
  grid_id: string;
  kecamatan: string;
  incidents: number;
  share_percent: number;
  first_date: string;
  last_date: string;
  /** Jarak hari antara kejadian pertama dan terakhir di grid ini. */
  span_days: number;
};

export type RepeatProfile = {
  grids_with_incidents: number;
  repeat_grids: number;
  single_incident_grids: number;
  incidents_in_repeat_grids: number;
  share_percent: number;
  denominator: number;
  grids: RepeatGrid[];
  basis: string;
};

export type PatternProfile = {
  threat_type: string;
  incidents: number;
  date_from: string | null;
  date_to: string | null;
  /** Berapa persen poin yang diwakili satu kejadian — ukuran kerapuhan persentasenya. */
  sample_note: string;
  where: PatternDistribution[];
  when: PatternDistribution[];
  how: PatternDistribution[];
  target: PatternDistribution[];
  repeat: RepeatProfile;
  time_basis: string;
};

export type ThreatTypeCount = { threat_type: string; incidents: number };

export type PatternDnaResponse = {
  threat_types: ThreatTypeCount[];
  threat_type: string | null;
  profile: PatternProfile | null;
  source: {
    table: string;
    date_from: string | null;
    date_to: string | null;
    incidents: number;
    /** Polsek pengguna bila cakupannya dibatasi wilayah, `null` bila tidak. */
    scope: string | null;
  };
  scope_basis: string;
  analysis_basis: string;
};

/**
 * Mengambil daftar jenis, atau profil satu jenis bila `threatType` diisi.
 *
 * Backend menolak jenis yang tidak ada di dalam cakupan pengguna dengan 400. Halaman
 * karena itu memilih jenisnya dari daftar yang sudah diterima (`resolveThreatType`),
 * bukan meneruskan isi alamat apa adanya.
 */
export function getPatternDna(threatType: string | null): Promise<PatternDnaResponse> {
  const query = threatType === null ? "" : `?threat_type=${encodeURIComponent(threatType)}`;
  return apiGet<PatternDnaResponse>(`/analytics/crime-pattern-dna${query}`);
}
