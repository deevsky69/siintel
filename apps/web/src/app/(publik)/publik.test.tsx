import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PublicSummary } from "@/lib/warga";
import type { ReportOptions } from "./lapor/actions";
import { ReportForm } from "./lapor/report-form";
import BerandaWarga from "./page";

/**
 * Halaman warga SIGAP WARGA (2 November 2026): hanya memuat yang diputuskan boleh terbuka
 * — tingkat kasar dan angka historis — dan tidak pernah memuat skor, prediksi, atau titik.
 */

const summary: PublicSummary = {
  window_from: "2025-01-01",
  window_to: "2025-12-31",
  months: [
    "2025-01",
    "2025-02",
    "2025-03",
    "2025-04",
    "2025-05",
    "2025-06",
    "2025-07",
    "2025-08",
    "2025-09",
    "2025-10",
    "2025-11",
    "2025-12",
  ],
  threat_types: ["CURANMOR", "CURAT", "CURAS"],
  level_edges: { low_max: 3, high_min: 12 },
  areas: [
    {
      kelurahan: "Tebet Timur",
      kecamatan: "Tebet",
      polsek: "Tebet",
      total: 14,
      level: "TINGGI",
      by_threat: { CURANMOR: 9, CURAT: 4, CURAS: 1 },
      by_month: [1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1],
      rating: 3.5,
      rating_count: 4,
    },
  ],
  kecamatan: [
    {
      kecamatan: "Tebet",
      total: 14,
      kelurahan: 1,
      by_threat: { CURANMOR: 9, CURAT: 4, CURAS: 1 },
      level: "TINGGI",
    },
  ],
  status: "PROPOSED",
  basis: "Tingkat RENDAH/SEDANG/TINGGI adalah pembagian tertil (PROPOSED).",
};

const imbauan = vi.hoisted(() => ({
  rows: [
    {
      code: "PAL-0026",
      threat_type: "CURANMOR",
      area_text: "Kecamatan Tebet",
      time_window: "18:00-23:59",
      message: "Kunci ganda kendaraan Anda dan parkir di tempat terang.",
    },
  ],
}));

vi.mock("./lapor/actions", () => ({
  getImbauanPublik: vi.fn(async () => imbauan.rows),
  getReportOptions: vi.fn(),
  submitReport: vi.fn(),
  uploadAttachment: vi.fn(),
}));
vi.mock("@/lib/warga", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/warga")>();
  return { ...actual, getPublicSummary: vi.fn(async () => summary) };
});

describe("beranda SIGAP WARGA", () => {
  it("menawarkan lapor dan darurat 110, dengan peta sebagai isi utama", async () => {
    render(await BerandaWarga());

    expect(screen.getByRole("link", { name: /lapor kejadian/i })).toBeDefined();
    expect(screen.getByRole("link", { name: /darurat/i }).getAttribute("href")).toBe("tel:110");
    expect(screen.getByRole("group", { name: /peta tingkat kerawanan/i })).toBeDefined();
  });

  it("hanya memuat tingkat kasar dan imbauan yang sudah diterbitkan — tanpa skor atau prediksi", async () => {
    const { container } = render(await BerandaWarga());

    expect(screen.getByText(/Kunci ganda kendaraan/)).toBeDefined();
    expect(screen.getAllByText(/Kerawanan Tinggi/).length).toBeGreaterThan(0);
    const text = container.textContent ?? "";
    for (const forbidden of ["risk_score", "confidence", "prediksi untuk", "PRD-", "WRN-"]) {
      expect(text).not.toContain(forbidden);
    }
  });

  it("menyorot kelurahan yang sudah diulas pada Survey Rasa Aman", async () => {
    render(await BerandaWarga());

    expect(screen.getByRole("link", { name: "Tebet Timur" })).toBeDefined();
    expect(screen.getByText("(4)")).toBeDefined();
  });
});

describe("formulir laporan", () => {
  const options: ReportOptions = {
    categories: ["Kejahatan Jalanan"],
    kecamatan: ["Tebet"],
    areas: [
      {
        kecamatan: "Tebet",
        kelurahan: [{ name: "Tebet Timur", latitude: -6.22, longitude: 106.86 }],
      },
    ],
    max_description: 1000,
    area_basis: "",
    coordinate_basis: "",
    intake_basis: "",
    attachment_basis: "",
    max_attachments: 3,
    max_attachment_bytes: 1,
  } as ReportOptions;

  it("mengarahkan keadaan darurat ke 110 dan tidak meminta identitas", () => {
    const { container } = render(<ReportForm options={options} />);

    const names = [...container.querySelectorAll("input, textarea, select")].map(
      (el) => (el as HTMLInputElement).name,
    );
    for (const forbidden of ["nama", "name", "telepon", "phone", "nik", "email"]) {
      expect(names).not.toContain(forbidden);
    }
  });
});
