import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { formatWib, type PredictionDetail, type WarningDetail } from "@/lib/warnings";
import { ExplainabilityPanel } from "./explainability";
import { WarningBoard, type WarningGroup } from "./warning-board";

const active: WarningDetail = {
  code: "WRN-0053",
  severity: "CRITICAL",
  threat_type: "CURANMOR",
  time_window: "18:00-23:59",
  window_start: "2025-12-16T11:00:00Z",
  window_end: "2025-12-16T17:00:00Z",
  risk_score: 95,
  confidence: 89,
  status: "ACTIVE",
  created_at: "2026-09-01T02:05:40Z",
  kecamatan: "Setiabudi",
  kelurahan: "Kuningan Timur",
  grid_id: "JKS-028",
  prediction_code: "PRD-00111",
  threshold_version: "dummy-v1",
};

const acknowledged: WarningDetail = {
  ...active,
  code: "WRN-0017",
  severity: "WATCH",
  threat_type: "CURAT",
  risk_score: 62,
  confidence: null,
  status: "ACKNOWLEDGED",
  kecamatan: "Pasar Minggu",
  kelurahan: "Ragunan",
  grid_id: "JKS-015",
  prediction_code: "PRD-00035",
};

const prediction: PredictionDetail = {
  code: "PRD-00111",
  prediction_date: "2025-12-16",
  forecast_horizon: "6H",
  threat_type: "CURANMOR",
  time_window: "18:00-23:59",
  risk_score: 95,
  confidence: 89,
  dominant_factors: [
    { factor: "historical_incident_density", contribution: 0.378, source: "RULE" },
    { factor: "recent_incident_trend", contribution: 0.185, source: "RULE" },
  ],
  model_version: "dummy-v1",
  status: "PUBLISHED",
  kecamatan: "Setiabudi",
  kelurahan: "Kuningan Timur",
  grid_id: "JKS-028",
};

const groups: WarningGroup[] = [
  { status: "ACTIVE", rows: [active], total: 41 },
  { status: "ACKNOWLEDGED", rows: [acknowledged], total: 1 },
  { status: "RESOLVED", rows: [], total: 0 },
];

describe("papan peringatan", () => {
  it("mengelompokkan peringatan menurut status", () => {
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    expect(screen.getByText(/Peringatan Aktif/i)).toBeDefined();
    expect(screen.getByText(/Peringatan Sudah Diterima/i)).toBeDefined();
    expect(screen.getByText(/Peringatan Selesai/i)).toBeDefined();
  });

  it("menampilkan isi kartu peringatan sesuai data API", () => {
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    const card = screen.getByRole("link", { name: /WRN-0053/ });

    expect(card.textContent).toMatch(/Kritis/);
    expect(card.textContent).toMatch(/CURANMOR/);
    expect(card.textContent).toMatch(/Setiabudi.*Kuningan Timur/);
    expect(card.textContent).toMatch(/JKS-028/);
    expect(card.textContent).toMatch(/95/);
    expect(card.textContent).toMatch(/89%/);
    expect(card.textContent).toMatch(/18:00-23:59/);
    expect(card.textContent).toMatch(/dummy-v1/);
  });

  it("memakai label tingkat peringatan berbahasa Indonesia", () => {
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    expect(screen.getByText("Waspada")).toBeDefined();
  });

  it("menyatakan keadaan kosong dengan kata, bukan angka nol", () => {
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    expect(screen.getByText("Tidak ada peringatan berstatus Selesai.")).toBeDefined();
    expect(screen.getByText("tidak ada")).toBeDefined();
  });

  it("menampilkan versi ambang dan menandainya belum final", () => {
    // CLAUDE.md §11: ambang DEMO/PROPOSED tidak boleh terbaca sebagai ketetapan.
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    expect(screen.getByText("DEMO / PROPOSED")).toBeDefined();
    expect(screen.getAllByText("dummy-v1").length).toBeGreaterThan(0);
    expect(screen.getByText(/belum ditetapkan secara resmi/i)).toBeDefined();
  });

  it("menandai peringatan yang sedang dipilih pada tautannya", () => {
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    const link = screen.getByRole("link", { name: /WRN-0053/ });
    expect(link.getAttribute("aria-current")).toBe("true");
    expect(link.getAttribute("href")).toBe("/peringatan?dipilih=WRN-0053");
  });

  it("menyatakan bahwa tombol tindak lanjut belum berfungsi", () => {
    // Tombol yang tampak berfungsi padahal tidak akan menjadikan halaman ini mockup.
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    const acknowledge = screen.getByRole("button", { name: /terima peringatan/i });
    const resolve = screen.getByRole("button", { name: /nyatakan selesai/i });

    expect(acknowledge.hasAttribute("disabled")).toBe(true);
    expect(resolve.hasAttribute("disabled")).toBe(true);
    expect(screen.getByText(/menunggu TASK 111/i)).toBeDefined();
  });

  it("menyatakan peringatan bukan perintah operasional", () => {
    // CLAUDE.md §13.
    render(<WarningBoard groups={groups} selected={active} sourcePrediction={prediction} />);

    expect(screen.getByText(/hanya lahir setelah keputusan pejabat berwenang/i)).toBeDefined();
  });
});

describe("panel dasar peringatan", () => {
  it("menampilkan prediksi sumber beserta faktor dominannya", () => {
    render(<ExplainabilityPanel warning={active} prediction={prediction} />);

    expect(screen.getAllByText("PRD-00111").length).toBeGreaterThan(0);
    expect(screen.getByText("Kepadatan kejadian historis")).toBeDefined();
    expect(screen.getByText("0,378")).toBeDefined();
    expect(screen.getByText("dummy-v1")).toBeDefined();
  });

  it("menampilkan asal tiap faktor dan tidak menyamarkan hasil aturan sebagai temuan model", () => {
    // CLAUDE.md §27: WHY harus berasal dari mekanisme yang benar-benar dipakai.
    render(<ExplainabilityPanel warning={active} prediction={prediction} />);

    expect(screen.getAllByText("RULE").length).toBeGreaterThan(0);
    expect(screen.getByText(/bukan temuan model terlatih/i)).toBeDefined();
  });

  it("membedakan penjelasan yang berasal dari model", () => {
    render(
      <ExplainabilityPanel
        warning={active}
        prediction={{
          ...prediction,
          dominant_factors: [
            { factor: "spatial_concentration", contribution: 0.42, source: "MODEL" },
          ],
        }}
      />,
    );

    expect(screen.getAllByText("MODEL").length).toBeGreaterThan(0);
    expect(screen.getByText(/kontribusi fitur pada model/i)).toBeDefined();
  });

  it("menyatakan apa adanya bila prediksi sumbernya tidak termuat", () => {
    render(<ExplainabilityPanel warning={active} prediction={null} />);

    expect(screen.getByText(/tidak dapat ditampilkan/i)).toBeDefined();
  });

  it("menyatakan bila tidak ada peringatan yang dipilih", () => {
    render(<ExplainabilityPanel warning={null} prediction={null} />);

    expect(screen.getByText(/tidak ada peringatan yang dipilih/i)).toBeDefined();
  });
});

describe("format waktu", () => {
  it("menampilkan waktu dalam WIB", () => {
    expect(formatWib("2025-12-16T11:00:00Z")).toMatch(/WIB$/);
    expect(formatWib("2025-12-16T11:00:00Z")).toMatch(/2025/);
  });

  it("menandai waktu yang tidak ada, bukan mengarang tanggal", () => {
    expect(formatWib(null)).toBe("—");
    expect(formatWib("bukan tanggal")).toBe("—");
  });
});
