import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PublicSummary } from "@/lib/warga";
import { MapCanvas } from "./map-canvas";

/**
 * Kanvas beranda (3 November 2026): chip saring meredupkan wilayah lain, wilayah yang
 * disentuh memunculkan kartu kecil, dan keadaan kosong/gagal tetap menawarkan jalan keluar.
 */

const summary: PublicSummary = {
  window_from: "2025-01-01",
  window_to: "2025-12-31",
  months: [],
  threat_types: ["CURANMOR"],
  level_edges: { low_max: 3, high_min: 12 },
  areas: [],
  kecamatan: [
    { kecamatan: "Tebet", total: 14, kelurahan: 7, by_threat: {}, level: "TINGGI" },
    { kecamatan: "Setiabudi", total: 2, kelurahan: 8, by_threat: {}, level: "RENDAH" },
  ],
  status: "PROPOSED",
  basis: "",
};

describe("MapCanvas", () => {
  it("chip tingkat meredupkan wilayah lain dan dapat dilepas lagi", () => {
    render(<MapCanvas summary={summary} imbauan={[]} />);

    const tinggi = screen.getByRole("button", { name: /Tinggi/ });
    expect(screen.getByRole("button", { name: /Semua/ }).getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(tinggi);
    expect(tinggi.getAttribute("aria-pressed")).toBe("true");
    const setiabudi = screen.getByRole("link", { name: /^Setiabudi/ });
    const tebet = screen.getByRole("link", { name: /^Tebet/ });
    expect(setiabudi.querySelector("polygon")?.getAttribute("fill-opacity")).toBe("0.12");
    expect(tebet.querySelector("polygon")?.getAttribute("fill-opacity")).toBe("0.5");

    fireEvent.click(tinggi);
    expect(tinggi.getAttribute("aria-pressed")).toBe("false");
    expect(setiabudi.querySelector("polygon")?.getAttribute("fill-opacity")).toBe("0.5");
  });

  it("menampilkan kartu kecil saat wilayah difokus", () => {
    render(<MapCanvas summary={summary} imbauan={[]} />);

    fireEvent.focus(screen.getByRole("link", { name: /^Tebet/ }));
    const tip = screen.getByRole("status");
    expect(tip.textContent).toContain("Tebet");
    expect(tip.textContent).toContain("14 kejadian");
  });

  it("tanpa ringkasan: tetap menawarkan lapor dan 110, tanpa chip", () => {
    render(<MapCanvas summary={null} imbauan={[]} />);

    expect(screen.getByText(/Peta belum dapat dimuat/)).toBeDefined();
    expect(screen.queryByRole("button", { name: /Semua/ })).toBeNull();
    expect(screen.getByRole("link", { name: /lapor kejadian/i })).toBeDefined();
    expect(screen.getByText(/Tidak ada imbauan khusus/)).toBeDefined();
  });
});
