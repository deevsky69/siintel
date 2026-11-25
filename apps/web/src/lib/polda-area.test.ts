import { describe, expect, it } from "vitest";
import { AREA_LINKS, AREA_UNIT, poldaHref, UNIT_AREA } from "./polda-area";
import { HOME_AREA, shapesAt } from "./wilayah";

describe("padanan satuan rekap Polda dengan wilayah peta", () => {
  it("setiap wilayah padanan memang ada pada peta tingkat Polda, tanpa ganda", () => {
    const onMap = new Set(shapesAt("polda").map((shape) => shape.name));
    const areas = Object.values(UNIT_AREA);
    expect(areas.every((area) => onMap.has(area))).toBe(true);
    expect(new Set(areas).size).toBe(areas.length);
    expect(AREA_UNIT[HOME_AREA]).toBe("Polres Metro Jakarta Selatan");
  });

  it("wilayah lain pada peta membuka rincian Polres yang membawahinya", () => {
    expect(AREA_LINKS["Jakarta Timur"]).toBe(poldaHref("Polres Metro Jakarta Timur"));
    expect(AREA_LINKS["Kota Depok"]).toBe("/ops/polda?polres=Polres%20Metro%20Depok");
    // Kabupaten Tangerang ada di peta tetapi bukan satuan tersendiri pada rekap.
    expect(AREA_LINKS["Kabupaten Tangerang"]).toBeUndefined();
  });
});
