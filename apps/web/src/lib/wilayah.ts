/**
 * Wilayah pada peta: tiga lapisan di atas satu sistem koordinat.
 *
 * ```text
 * polda      12 kota/kabupaten wilayah hukum Polda Metro Jaya
 * kecamatan  10 kecamatan Jakarta Selatan
 * kelurahan  65 kelurahan, masing-masing menyebut kecamatan induknya
 * ```
 *
 * Bentuknya dibangkitkan `scripts/bangun-batas-wilayah.py` dari OpenStreetMap dan disimpan
 * di `wilayah.generated.ts`. Ini **batas administratif sungguhan** — menggantikan poligon
 * perkiraan hasil pembagian Voronoi yang dipakai sebelumnya.
 *
 * ## Satu sistem koordinat untuk semuanya
 *
 * Ketiga lapisan berada pada koordinat yang sama: 1 satuan = 10 meter, sumbu Y menghadap ke
 * bawah. Karena itu menyelami peta cukup dengan mengubah `viewBox` SVG — tidak ada bentuk
 * yang dihitung ulang, dan titik berkoordinat lintang/bujur jatuh di tempat yang sama pada
 * setiap tingkat. Kalau tiap lapisan punya sistemnya sendiri, satu titik kejadian akan
 * berpindah tempat ketika pengguna menyelam, dan tidak ada cara membuktikan mana yang benar.
 */

import {
  type AreaShape,
  KECAMATAN_SHAPES,
  KELURAHAN_SHAPES,
  POLDA_SHAPES,
  PROJECTION,
} from "./wilayah.generated";

export type { AreaShape };

export type MapLevel = "polda" | "kecamatan" | "kelurahan";

export type MapPoint = readonly [x: number, y: number];

export type Bounds = {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
};

/**
 * Wilayah hukum Polres Metro Jakarta Selatan di dalam peta Polda Metro Jaya.
 *
 * Satu-satunya wilayah yang diwarnai penuh pada lapisan teratas; sebelas lainnya digambar
 * tembus pandang. Sistem ini memang hanya memegang data Jakarta Selatan, dan mewarnai
 * wilayah lain akan menyiratkan pengetahuan yang tidak dimilikinya.
 */
export const HOME_AREA = "Jakarta Selatan";

/**
 * Wilayah yang ikut digambar tetapi **tidak ikut menentukan bingkai**.
 *
 * Kepulauan Seribu memang bagian dari wilayah hukum Polda Metro Jaya, dan menghapusnya
 * akan menggambarkan wilayah hukum yang salah. Tetapi gugusannya membentang sekitar 80
 * kilometer ke utara, sementara seluruh daratan Jabodetabek hanya selebar itu: memasukkan
 * keduanya ke satu bingkai membuat daratannya — tempat seluruh data berada — mengerut
 * menjadi seperempat layar.
 *
 * Ia karena itu tetap digambar pada koordinatnya yang sebenarnya, hanya tidak menarik
 * bingkai. Bagian yang berada di luar bingkai tidak tampak, dan kaki peta menyebutkannya.
 */
export const OFF_FRAME_AREAS: readonly string[] = ["Kepulauan Seribu"];

const LEVELS: Record<MapLevel, readonly AreaShape[]> = {
  polda: POLDA_SHAPES,
  kecamatan: KECAMATAN_SHAPES,
  kelurahan: KELURAHAN_SHAPES,
};

/** Wilayah pada satu lapisan; untuk kelurahan, disaring menurut kecamatan induk. */
export function shapesAt(level: MapLevel, parent?: string): readonly AreaShape[] {
  const shapes = LEVELS[level];
  if (level !== "kelurahan" || !parent) return shapes;
  return shapes.filter((shape) => shape.parent === parent);
}

export function shapeNamed(level: MapLevel, name: string): AreaShape | undefined {
  return LEVELS[level].find((shape) => shape.name === name);
}

/** Kecamatan induk sebuah kelurahan, bila namanya dikenal. */
export function parentOf(kelurahan: string): string | undefined {
  return KELURAHAN_SHAPES.find((shape) => shape.name === kelurahan)?.parent;
}

export function boundsOf(shapes: readonly AreaShape[]): Bounds {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const shape of shapes) {
    for (const ring of shape.rings) {
      for (const [x, y] of ring) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }

  // Kumpulan kosong menghasilkan bidang bersatuan, bukan `Infinity`: nilai tak hingga pada
  // atribut `viewBox` membuat SVG gagal digambar seluruhnya, dan penyebabnya sukar dilacak.
  if (!Number.isFinite(minX)) return { x: 0, y: 0, width: 1, height: 1 };

  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

/**
 * Bidang gambar untuk sekumpulan wilayah, dengan ruang napas di tepinya.
 *
 * Ruangnya dihitung dari sisi terpanjang, bukan masing-masing sumbu, supaya wilayah yang
 * jangkung tidak mendapat bantalan kiri-kanan yang jauh lebih tebal daripada atas-bawah.
 */
export function framingShapes(shapes: readonly AreaShape[]): readonly AreaShape[] {
  const framing = shapes.filter((shape) => !OFF_FRAME_AREAS.includes(shape.name));
  // Bila yang tersisa kosong — misalnya lapisan hanya berisi wilayah luar bingkai — bingkai
  // dihitung dari semuanya, karena peta tanpa bingkai sama sekali tidak dapat digambar.
  return framing.length > 0 ? framing : shapes;
}

export function viewBoxOf(shapes: readonly AreaShape[], paddingRatio = 0.05): string {
  const { x, y, width, height } = boundsOf(framingShapes(shapes));
  const padding = Math.max(width, height) * paddingRatio;
  return `${x - padding} ${y - padding} ${width + padding * 2} ${height + padding * 2}`;
}

/** Simpul poligon sebagai atribut `points` SVG. */
export function polygonPoints(ring: readonly MapPoint[]): string {
  return ring.map(([x, y]) => `${x},${y}`).join(" ");
}

/**
 * Menaruh koordinat lintang/bujur pada sistem koordinat peta.
 *
 * Proyeksi equirectangular: bujur dikalikan kosinus lintang acuan supaya jarak timur-barat
 * dan utara-selatan sebanding. Untuk bentang selebar wilayah hukum ini penyimpangannya
 * jauh di bawah ketelitian yang dituntut peta sebaran.
 */
export function projectLatLon(latitude: number, longitude: number): MapPoint {
  return [
    ((longitude - PROJECTION.originLongitude) *
      PROJECTION.cosReferenceLatitude *
      PROJECTION.metresPerDegree) /
      PROJECTION.metresPerUnit,
    ((PROJECTION.originLatitude - latitude) * PROJECTION.metresPerDegree) /
      PROJECTION.metresPerUnit,
  ];
}

/** Apakah sebuah titik berada di dalam bidang gambar yang sedang tampil. */
export function isWithin([x, y]: MapPoint, bounds: Bounds): boolean {
  return (
    x >= bounds.x && x <= bounds.x + bounds.width && y >= bounds.y && y <= bounds.y + bounds.height
  );
}

/**
 * Letak sebuah titik dalam persen terhadap bidang gambar.
 *
 * Dipakai untuk menaruh label sebagai HTML **di atas** peta, bukan sebagai `<text>` di
 * dalamnya: ukuran huruf di dalam SVG ikut mengecil bersama `viewBox`, sehingga tidak ada
 * satu nilai pun yang terbaca pada semua tingkat penyelaman.
 */
export function toPercent([x, y]: MapPoint, bounds: Bounds): { left: string; top: string } {
  return {
    left: `${((x - bounds.x) / bounds.width) * 100}%`,
    top: `${((y - bounds.y) / bounds.height) * 100}%`,
  };
}

/**
 * Lebar ruang yang benar-benar tersedia untuk label sebuah wilayah, dalam satuan proyeksi.
 *
 * Bukan lebar kotak pembatas. Kotak pembatas Mampang Prapatan hampir dua kali lebar
 * wilayahnya pada ketinggian tempat namanya duduk, sehingga membatasi label dengannya
 * tetap membiarkan nama menjulur ke wilayah tetangga — persis keluhan yang membuat fungsi
 * ini ada.
 *
 * Yang dihitung adalah **potongan mendatar** poligon tepat pada ketinggian jangkar label:
 * seluruh perpotongan sisi dengan garis `y = jangkar.y` diurutkan, lalu diambil selang
 * yang memuat jangkar itu sendiri. Selang itulah lebar wilayah di tempat nama akan
 * digambar. Cincin dalam (lubang) ikut memotong, jadi selangnya berhenti di tepi lubang —
 * sebagaimana seharusnya.
 *
 * Menjawab `0` bila jangkar ternyata tidak berada di dalam satu selang pun; pemanggil
 * memutuskan lantai minimumnya sendiri, karena lebar terkecil yang masih pantas dibaca
 * adalah keputusan tampilan, bukan keputusan geometri.
 */
export function labelSpan(shape: AreaShape): number {
  const [anchorX, anchorY] = shape.label;
  const crossings: number[] = [];

  for (const ring of shape.rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      // Aturan yang sama dengan uji titik-dalam-poligon: satu ujung di atas garis dan satu
      // di bawah. Menyamakan `>=` di kedua sisi akan menghitung ganda setiap simpul yang
      // kebetulan tepat menyentuh garis.
      if (yi > anchorY !== yj > anchorY) {
        crossings.push(xi + ((anchorY - yi) * (xj - xi)) / (yj - yi));
      }
    }
  }

  crossings.sort((a, b) => a - b);

  for (let i = 0; i + 1 < crossings.length; i += 2) {
    if (anchorX >= crossings[i] && anchorX <= crossings[i + 1]) {
      return crossings[i + 1] - crossings[i];
    }
  }

  return 0;
}
