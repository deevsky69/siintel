/**
 * Padanan satuan pada rekap Polda dengan wilayah pada peta tingkat Polda, dan alamat rincian
 * tiap Polres. Modul ini TANPA impor supaya boleh dipakai komponen klien (peta); `polda.ts`
 * mengimpor `./api` dan karenanya tidak boleh.
 *
 * Tiga Polres tidak punya poligon sendiri (pelabuhan, bandara) atau berada di luar bingkai
 * (Kepulauan Seribu); ketiganya tetap dapat dibuka dari tabel. Kabupaten Tangerang ada di
 * peta tetapi tidak tercantum sebagai satuan tersendiri pada rekap.
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

/** Alamat rincian satu satuan pada halaman rekap Polda. */
export const poldaHref = (unit: string) => `/ops/polda?polres=${encodeURIComponent(unit)}`;

/** Wilayah peta → alamat rincian Polres yang membawahinya. */
export const AREA_LINKS: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(UNIT_AREA).map(([unit, area]) => [area, poldaHref(unit)]),
);

/** Wilayah peta → nama satuan. */
export const AREA_UNIT: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(UNIT_AREA).map(([unit, area]) => [area, unit]),
);
