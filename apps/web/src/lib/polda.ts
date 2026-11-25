import { apiGet } from "./api";

/** Rekap kriminalitas Polda Metro Jaya per Polres (catatan 196) — data agregat Pusiknas. */
export type RecapCount = { ct: number; cc: number; cr: number | null; share_pct?: number | null };

export type RecapThreeC = RecapCount & {
  curat: number;
  curas: number;
  curanmor: number;
  /** Porsi 3C terhadap seluruh kriminalitas satuan itu. */
  of_overall_pct?: number | null;
};

export type RecapUnit = {
  name: string;
  kind: "POLRES" | "SATKER";
  /** Satuan pemilik aplikasi ini. */
  home: boolean;
  overall: Record<string, RecapCount>;
  c3: Record<string, RecapThreeC>;
  change_overall_pct: number | null;
  change_c3_pct: number | null;
  /** Peringkat di antara Polres menurut CT tahun berjalan; kosong untuk satuan kerja Polda. */
  rank_c3?: number;
  rank_overall?: number;
};

export type PoldaRecap =
  | { available: false; home_unit: string; basis: string }
  | {
      available: true;
      position_at: string;
      source: string;
      source_sha256: string | null;
      imported_at: string;
      imported_by: string | null;
      years: number[];
      current_year: number;
      current_until: string;
      home_unit: string;
      polres_count: number;
      units: RecapUnit[];
      totals: { overall: Record<string, RecapCount>; c3: Record<string, RecapThreeC> };
      equal_period: {
        label: string;
        overall: Record<string, RecapCount>;
        c3: Record<string, RecapCount>;
      } | null;
      monthly: { month: number; overall: Record<string, number>; c3: Record<string, number> }[];
      settlements: { form: string; counts: Record<string, number> }[];
      top_types: Record<string, { rank: number; name: string; ct: number }[]>;
      basis: string;
    };

export const getPoldaRecap = () => apiGet<PoldaRecap>("/polda/recap");

/**
 * Padanan nama satuan pada rekap dengan wilayah pada peta tingkat Polda. Tiga Polres tidak
 * punya poligon sendiri (pelabuhan, bandara) atau berada di luar bingkai (Kepulauan Seribu);
 * ketiganya tetap tampil pada tabel. Kabupaten Tangerang ada di peta tetapi tidak ada pada
 * rekap sebagai satuan tersendiri.
 */
export const UNIT_AREA: Readonly<Record<string, string>> = {
  "Polres Metro Jakarta Selatan": "Jakarta Selatan",
  "Polres Metro Jakarta Timur": "Jakarta Timur",
  "Polres Metro Jakarta Pusat": "Jakarta Pusat",
  "Polres Metro Jakarta Barat": "Jakarta Barat",
  "Polres Metro Jakarta Utara": "Jakarta Utara",
  "Polres Metro Tangerang Kota": "Kota Tangerang",
  "Polres Tangerang Selatan": "Kota Tangerang Selatan",
  "Polres Metro Bekasi Kota": "Kota Bekasi",
  "Polres Metro Bekasi": "Kabupaten Bekasi",
  "Polres Metro Depok": "Kota Depok",
  "Polres Kepulauan Seribu": "Kepulauan Seribu",
};
