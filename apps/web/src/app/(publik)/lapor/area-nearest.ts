/**
 * Mencari kelurahan terdekat dari sebuah titik — murni, tanpa jaringan, supaya dapat diuji.
 *
 * Dipakai formulir laporan untuk MENGUSULKAN kelurahan bila pelapor membagikan lokasinya
 * dari peramban: pada laptop, lokasi peramban datang dari Wi-Fi/IP dan melesetnya bisa
 * ratusan meter, jadi hasilnya usulan yang dapat dikoreksi — bukan kepastian. Backend
 * mengulang pencarian yang sama dengan PostGIS bila pelapor tidak memilih sendiri.
 */

export type AreaOption = {
  kecamatan: string;
  kelurahan: { name: string; latitude: number; longitude: number }[];
};

export type NearestArea = { kecamatan: string; kelurahan: string; distanceM: number };

const EARTH_RADIUS_M = 6_371_000;

export function distanceMeters(
  a: { latitude: number; longitude: number },
  b: { latitude: number; longitude: number },
): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

export function nearestArea(
  areas: AreaOption[],
  point: { latitude: number; longitude: number },
): NearestArea | null {
  let best: NearestArea | null = null;
  for (const area of areas) {
    for (const kel of area.kelurahan) {
      const distanceM = distanceMeters(point, kel);
      if (best === null || distanceM < best.distanceM) {
        best = { kecamatan: area.kecamatan, kelurahan: kel.name, distanceM };
      }
    }
  }
  return best;
}
