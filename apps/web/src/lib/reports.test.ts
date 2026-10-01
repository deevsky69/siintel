import { describe, expect, it } from "vitest";
import { JAM_TIDAK_TERCATAT, jamKejadian } from "./reports";

describe("jamKejadian", () => {
  it("memotong detik dari jam yang tercatat", () => {
    expect(jamKejadian({ incident_time: "13:51:00", time_known: true })).toBe("13:51");
  });

  it("tidak mengarang jam ketika Laporan Polisi tidak mencatatnya", () => {
    // 21,9% data asli Pusiknas tidak punya jam; sebelumnya `.slice` pada null menjatuhkan halaman.
    expect(jamKejadian({ incident_time: null, time_known: false })).toBe(JAM_TIDAK_TERCATAT);
  });

  it("memperlakukan jam 00:00 yang ditandai tidak tercatat sebagai tidak tercatat", () => {
    expect(jamKejadian({ incident_time: "00:00:00", time_known: false })).toBe(JAM_TIDAK_TERCATAT);
  });
});
