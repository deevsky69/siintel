import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PanduanPage from "./page";

/**
 * Halaman Panduan (17 November 2026, naskah Taskap 4.7 b dan f): langkah pengamanan per jenis
 * tempat dengan pola agregat, dan cara berlangganan imbauan — tanpa skor maupun alamat.
 */

const guides = vi.hoisted(() => ({
  value: null as unknown,
}));

vi.mock("@/lib/warga", () => ({
  getSecurityGuides: vi.fn(async () => {
    if (guides.value === null) throw new Error("API 500");
    return guides.value;
  }),
}));

const body = {
  status: "PROPOSED",
  closing: "Keadaan darurat: 110.",
  basis: "Panduan umum; pola agregat 12 bulan terakhir.",
  data: [
    {
      id: "kos",
      title: "Kos, kontrakan, dan asrama",
      audience: "Pemilik, pengelola, dan penghuni",
      steps: ["Sediakan parkir motor di dalam pagar yang terkunci.", "Pasang lampu."],
      pattern: {
        incidents: 41,
        share_pct: 3.3,
        top_modus: [{ modus: "Menggunakan kunci palsu", count: 20 }],
        peak_block: "03.00-06.00",
        peak_block_count: 12,
        with_time: 33,
        from: "2025-01-01",
        to: "2025-12-31",
      },
    },
    {
      id: "rtrw",
      title: "Lingkungan RT/RW dan rumah tinggal",
      audience: "Pengurus RT/RW dan warga",
      steps: ["Aktifkan siskamling."],
      pattern: {
        incidents: 0,
        share_pct: null,
        top_modus: [],
        peak_block: null,
        peak_block_count: 0,
        with_time: 0,
        from: "2025-01-01",
        to: "2025-12-31",
      },
    },
  ],
};

describe("Panduan pengamanan", () => {
  beforeEach(() => {
    guides.value = body;
  });

  it("memuat langkah tiap panduan dan pola agregatnya", async () => {
    render(await PanduanPage());
    expect(screen.getByRole("heading", { name: "Kos, kontrakan, dan asrama" })).toBeDefined();
    expect(screen.getByText("Sediakan parkir motor di dalam pagar yang terkunci.")).toBeDefined();
    const pattern = screen.getByText(/pencurian di jenis/);
    expect(pattern.textContent).toContain("41");
    expect(pattern.textContent).toContain("03.00-06.00");
    expect(pattern.textContent).toContain("menggunakan kunci palsu");
    // Panduan tanpa kejadian tercatat tidak mengarang kalimat pola.
    expect(screen.getAllByText(/pencurian di jenis/)).toHaveLength(1);
  });

  it("menjelaskan cara berlangganan dan apa yang disimpan", async () => {
    render(await PanduanPage());
    expect(screen.getByText("/langganan Tebet Timur")).toBeDefined();
    expect(screen.getByText("/berhenti")).toBeDefined();
    expect(screen.getByText(/tanpa nama dan tanpa/)).toBeDefined();
  });

  it("tetap menampilkan cara berlangganan bila panduan gagal dimuat", async () => {
    guides.value = null;
    render(await PanduanPage());
    expect(screen.getByText(/Panduan belum dapat dimuat/)).toBeDefined();
    expect(screen.getByText("/langganan Tebet Timur")).toBeDefined();
  });
});
