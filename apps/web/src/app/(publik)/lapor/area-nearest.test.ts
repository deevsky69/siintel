import { describe, expect, it } from "vitest";
import { type AreaOption, distanceMeters, nearestArea } from "./area-nearest";

const areas: AreaOption[] = [
  {
    kecamatan: "Tebet",
    kelurahan: [
      { name: "Tebet Barat", latitude: -6.2305, longitude: 106.8475 },
      { name: "Manggarai", latitude: -6.2105, longitude: 106.85 },
    ],
  },
  {
    kecamatan: "Kebayoran Baru",
    kelurahan: [{ name: "Senayan", latitude: -6.2275, longitude: 106.8015 }],
  },
];

describe("kelurahan terdekat dari lokasi peramban", () => {
  it("memilih titik pusat kelurahan yang paling dekat, lintas kecamatan", () => {
    const found = nearestArea(areas, { latitude: -6.228, longitude: 106.803 });
    expect(found?.kecamatan).toBe("Kebayoran Baru");
    expect(found?.kelurahan).toBe("Senayan");
    expect(found?.distanceM).toBeLessThan(500);
  });

  it("menjawab null bila tidak ada kelurahan untuk dibandingkan", () => {
    expect(nearestArea([], { latitude: 0, longitude: 0 })).toBeNull();
  });

  it("menghitung jarak dalam meter dengan wajar", () => {
    const d = distanceMeters(
      { latitude: -6.2305, longitude: 106.8475 },
      { latitude: -6.2105, longitude: 106.85 },
    );
    // Sekitar 2,2 km antara Tebet Barat dan Manggarai.
    expect(d).toBeGreaterThan(2000);
    expect(d).toBeLessThan(2500);
  });
});
