/**
 * Bentuk wilayah 9 kecamatan Polres Metro Jakarta Selatan untuk peta SVG.
 *
 * ## Ini BUKAN batas administratif resmi
 *
 * Poligon di bawah adalah **bentuk perkiraan** yang diturunkan dari 33 titik lokasi pada
 * tabel `locations` (endpoint `GET /locations`), bukan dari peta resmi BPS/Bakosurtanal.
 * Bentuknya cukup untuk membaca *sebaran* risiko antar kecamatan, tetapi **tidak boleh
 * dipakai untuk keperluan yang membutuhkan batas wilayah sebenarnya** — penetapan
 * yurisdiksi, penghitungan luas, atau produk kartografi.
 *
 * ## Cara bentuk ini dihitung (sekali, lalu dibekukan sebagai konstanta)
 *
 * 1. Titik lokasi diproyeksikan equirectangular (`x = bujur × cos(lintang acuan)`,
 *    `y = lintang`) sehingga perbandingan jarak timur-barat dan utara-selatan wajar.
 * 2. Garis luar wilayah = *convex hull* seluruh 33 titik, dimekarkan 16% dari pusatnya
 *    agar titik terluar tidak persis menempel di tepi peta.
 * 3. Setiap kecamatan diwakili rata-rata koordinat titik-titiknya, lalu bidang dibagi
 *    secara Voronoi: satu sel berisi seluruh area yang lebih dekat ke kecamatan itu
 *    daripada ke kecamatan lain. Pembagian dikerjakan dengan pemotongan setengah-bidang
 *    berulang (Sutherland–Hodgman) terhadap garis luar pada langkah 2.
 * 4. Hasilnya diskalakan ke `MAP_VIEWBOX` dan dibulatkan satu angka di belakang koma.
 *
 * Perhitungan dilakukan **satu kali di luar aplikasi** dan hasilnya disimpan di sini:
 * bentuk wilayah tidak berubah dari permintaan ke permintaan, sehingga tidak ada gunanya
 * menghitungnya ulang setiap halaman dimuat.
 *
 * ## Cara menggantinya bila GeoJSON resmi tersedia
 *
 * Ganti isi `KECAMATAN_SHAPES` dengan poligon hasil proyeksi GeoJSON resmi ke sistem
 * koordinat `MAP_VIEWBOX`, sesuaikan `MAP_VIEWBOX`, lalu hapus catatan "perkiraan" pada
 * komponen peta. Tidak ada berkas lain yang perlu diubah — komponen peta hanya membaca
 * `kecamatan`, `points`, dan `label` dari sini.
 */

/** Titik pada sistem koordinat `MAP_VIEWBOX`. */
export type MapPoint = readonly [x: number, y: number];

export type DistrictShape = {
  /** Nama kecamatan, harus sama persis dengan nilai `kecamatan` dari API. */
  readonly kecamatan: string;
  /** Simpul poligon, searah keliling. */
  readonly points: readonly MapPoint[];
  /** Titik jangkar label/tooltip — pusat massa poligon. */
  readonly label: MapPoint;
};

/**
 * Bidang gambar peta. Perbandingan 1000 : 1538 mengikuti bentang geografis wilayah
 * (±0,11° bujur × ±0,17° lintang), jadi peta memang lebih tinggi daripada lebar.
 */
export const MAP_VIEWBOX = { width: 1000, height: 1538 } as const;

export const KECAMATAN_SHAPES: readonly DistrictShape[] = [
  {
    kecamatan: "Cilandak",
    points: [
      [31, 833],
      [78.7, 949.5],
      [211, 1203.1],
      [537.4, 1037.2],
      [531.6, 744.3],
      [394.6, 652.8],
      [304.8, 646.7],
    ],
    label: [308.4, 906.1],
  },
  {
    kecamatan: "Jagakarsa",
    points: [
      [211, 1203.1],
      [314.6, 1401.6],
      [640.4, 1537.3],
      [775.3, 1164.3],
      [789.3, 1125.3],
      [537.4, 1037.2],
    ],
    label: [516.9, 1268.2],
  },
  {
    kecamatan: "Kebayoran Baru",
    points: [
      [431.7, 151.2],
      [163, 232.2],
      [304.8, 646.7],
      [394.6, 652.8],
      [545.8, 333.1],
    ],
    label: [358.3, 380.6],
  },
  {
    kecamatan: "Kebayoran Lama",
    points: [
      [0, 757.3],
      [31, 833],
      [304.8, 646.7],
      [163, 232.2],
      [146.1, 237.4],
      [33.7, 486],
    ],
    label: [137.2, 560.8],
  },
  {
    kecamatan: "Mampang Prapatan",
    points: [
      [545.8, 333.1],
      [394.6, 652.8],
      [531.6, 744.3],
      [678.6, 677.8],
      [686.7, 399.4],
    ],
    label: [563.7, 552.9],
  },
  {
    kecamatan: "Pancoran",
    points: [
      [929.8, 736.7],
      [1000, 542.6],
      [996.4, 445.6],
      [712.1, 392.8],
      [686.7, 399.4],
      [678.6, 677.8],
    ],
    label: [831.3, 558.4],
  },
  {
    kecamatan: "Pasar Minggu",
    points: [
      [789.3, 1125.3],
      [929.8, 736.7],
      [678.6, 677.8],
      [531.6, 744.3],
      [537.4, 1037.2],
    ],
    label: [708.5, 882.9],
  },
  {
    kecamatan: "Setiabudi",
    points: [
      [895.4, 11.2],
      [431.7, 151.2],
      [545.8, 333.1],
      [686.7, 399.4],
      [712.1, 392.8],
    ],
    label: [663.9, 202],
  },
  {
    kecamatan: "Tebet",
    points: [
      [996.4, 445.6],
      [988.8, 237.4],
      [932.6, 0],
      [895.4, 11.2],
      [712.1, 392.8],
    ],
    label: [883.8, 263.9],
  },
] as const;

/** Merangkai simpul menjadi nilai atribut `points` sebuah `<polygon>`. */
export function polygonPoints(shape: DistrictShape): string {
  return shape.points.map(([x, y]) => `${x},${y}`).join(" ");
}

/** Posisi titik dalam persen bidang gambar — dipakai menempatkan tooltip HTML. */
export function toPercent([x, y]: MapPoint): { left: string; top: string } {
  return {
    left: `${(x / MAP_VIEWBOX.width) * 100}%`,
    top: `${(y / MAP_VIEWBOX.height) * 100}%`,
  };
}
