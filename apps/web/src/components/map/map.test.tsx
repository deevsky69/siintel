import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DistrictDetail } from "@/components/map/district-detail";
import { RiskLegend, riskBands } from "@/components/map/legend";
import { RiskMap } from "@/components/map/risk-map";
import { KECAMATAN_SHAPES } from "@/lib/geo";
import type { MapData, PredictionRow, RiskScoreRow } from "@/lib/map-data";
import { buildDistrictIntel } from "@/lib/map-data";

function score(over: Partial<RiskScoreRow>): RiskScoreRow {
  return {
    code: "RS-00001",
    assessment_date: "2025-12-31",
    threat_type: "CURAT",
    time_window: "18:00-23:59",
    risk_score: 88,
    risk_class: "CRITICAL",
    kecamatan: "Kebayoran Baru",
    grid_id: "JKS-001",
    weights_version: "dummy-v1",
    ...over,
  };
}

const scores: RiskScoreRow[] = [
  score({ code: "RS-1", risk_score: 88, threat_type: "CURAT", time_window: "18:00-23:59" }),
  score({
    code: "RS-2",
    risk_score: 40,
    risk_class: "LOW",
    threat_type: "CURAT",
    time_window: "06:00-12:00",
  }),
  score({
    code: "RS-3",
    risk_score: 71,
    risk_class: "HIGH",
    threat_type: "CURANMOR",
    time_window: "12:00-18:00",
  }),
  score({
    code: "RS-4",
    risk_score: 30,
    risk_class: "LOW",
    threat_type: "CURAS",
    time_window: "00:00-06:00",
    kecamatan: "Tebet",
    grid_id: "JKS-020",
  }),
];

const prediction: PredictionRow = {
  code: "PRD-00116",
  prediction_date: "2025-12-30",
  forecast_horizon: "6H",
  threat_type: "CURANMOR",
  time_window: "18:00-23:59",
  risk_score: 54,
  confidence: 63,
  dominant_factors: [
    { factor: "historical_incident_density", source: "RULE", contribution: 0.378 },
    { factor: "recent_incident_trend", source: "MODEL", contribution: 0.185 },
  ],
  model_version: "dummy-v1",
  status: "PUBLISHED",
  kecamatan: "Kebayoran Baru",
  kelurahan: "Senayan",
  grid_id: "JKS-001",
};

const districts = buildDistrictIntel(scores, [prediction]);

const data: MapData = {
  assessmentDate: "2025-12-31",
  weightsVersion: "dummy-v1",
  horizon: "6H",
  districts,
};

const districtOf = (kecamatan: string) => districts.find((row) => row.kecamatan === kecamatan);

describe("penyusunan data peta", () => {
  it("menyertakan seluruh kecamatan pada peta, termasuk yang tanpa data", () => {
    expect(districts).toHaveLength(KECAMATAN_SHAPES.length);

    const kosong = districtOf("Cilandak");
    expect(kosong?.riskScore).toBeNull();
    expect(kosong?.threats).toEqual([]);
    expect(kosong?.predictions).toEqual([]);
  });

  it("mengambil skor tertinggi per jenis ancaman dan per jendela waktu", () => {
    const kebayoran = districtOf("Kebayoran Baru");

    expect(kebayoran?.riskScore).toBe(88);
    expect(kebayoran?.riskClass).toBe("CRITICAL");
    // CURAT muncul dua kali (88 dan 40) — yang diambil hanya yang tertinggi.
    expect(kebayoran?.threats).toEqual([
      { label: "CURAT", score: 88, gridId: "JKS-001" },
      { label: "CURANMOR", score: 71, gridId: "JKS-001" },
    ]);
    expect(kebayoran?.windows.map((row) => row.label)).toEqual([
      "18:00-23:59",
      "12:00-18:00",
      "06:00-12:00",
    ]);
  });

  it("hanya memasangkan prediksi pada kecamatannya sendiri", () => {
    expect(districtOf("Kebayoran Baru")?.predictions).toHaveLength(1);
    expect(districtOf("Tebet")?.predictions).toEqual([]);
  });
});

describe("legenda risiko", () => {
  it("menurunkan rentang dari tangga risiko, bukan menuliskannya ulang", () => {
    const bands = riskBands();

    expect(bands.map((band) => band.risk)).toEqual(["LOW", "MODERATE", "HIGH", "CRITICAL"]);
    expect(bands[0].min).toBe(0);
    expect(bands.at(-1)?.max).toBe(100);
  });

  it("menyatakan ambang masih berstatus DEMO / PROPOSED", () => {
    render(<RiskLegend />);

    expect(screen.getByText(/demo \/ proposed/i)).toBeDefined();
  });
});

describe("peta risiko", () => {
  it("menggambar seluruh kecamatan sebagai wilayah yang dapat difokus keyboard", () => {
    render(<RiskMap data={data} />);

    const areas = screen.getAllByRole("button", { name: /—/ });
    expect(areas).toHaveLength(KECAMATAN_SHAPES.length);
    for (const area of areas) {
      expect(area.getAttribute("tabindex")).toBe("0");
    }
  });

  it("memberi label wilayah berisi skor dan kelas risikonya", () => {
    render(<RiskMap data={data} />);

    expect(
      screen.getByRole("button", {
        name: "Kebayoran Baru — skor risiko 88 dari 100, kelas Kritis",
      }),
    ).toBeDefined();
  });

  it("menyatakan wilayah tanpa data sebagai tidak ada data, bukan nol", () => {
    render(<RiskMap data={data} />);

    expect(screen.getByRole("button", { name: "Cilandak — tidak ada data risiko" })).toBeDefined();
    expect(screen.queryByLabelText(/Cilandak — skor risiko 0/)).toBeNull();
  });

  it("menampilkan tooltip ringkas saat wilayah disentuh tetikus", () => {
    render(<RiskMap data={data} />);

    fireEvent.mouseOver(screen.getByRole("button", { name: /^Tebet —/ }));

    expect(screen.getByText("30/100 · Rendah")).toBeDefined();
  });

  it("menutup tooltip ketika tetikus meninggalkan wilayah", () => {
    render(<RiskMap data={data} />);
    const tebet = screen.getByRole("button", { name: /^Tebet —/ });

    fireEvent.mouseOver(tebet);
    fireEvent.mouseOut(tebet);

    expect(screen.queryByText("30/100 · Rendah")).toBeNull();
  });

  it("membuka rincian wilayah berisiko tertinggi sejak awal", () => {
    render(<RiskMap data={data} />);
    const detail = screen.getByRole("region", { name: /rincian wilayah terpilih/i });

    expect(within(detail).getByText("Kebayoran Baru")).toBeDefined();
    expect(within(detail).getAllByText("88").length).toBeGreaterThan(0);
  });

  it("mengganti rincian ketika wilayah lain diklik", () => {
    render(<RiskMap data={data} />);

    fireEvent.click(screen.getByRole("button", { name: /^Tebet —/ }));
    const detail = screen.getByRole("region", { name: /rincian wilayah terpilih/i });

    expect(within(detail).getByText("Tebet")).toBeDefined();
    expect(within(detail).getByText("CURAS")).toBeDefined();
  });

  it("dapat dipilih dengan papan ketik", () => {
    render(<RiskMap data={data} />);

    const tebet = screen.getByRole("button", { name: /^Tebet —/ });
    fireEvent.focus(tebet);
    fireEvent.keyDown(tebet, { key: "Enter" });

    const detail = screen.getByRole("region", { name: /rincian wilayah terpilih/i });
    expect(within(detail).getByText("Tebet")).toBeDefined();
    // Fokus papan ketik juga memunculkan keterangan ringkas yang sama dengan hover.
    expect(screen.getByText("30/100 · Rendah")).toBeDefined();
  });

  it("menyatakan keadaan kosong pada wilayah tanpa penilaian", () => {
    render(<RiskMap data={data} />);

    fireEvent.click(screen.getByRole("button", { name: /^Cilandak —/ }));
    const detail = screen.getByRole("region", { name: /rincian wilayah terpilih/i });

    expect(within(detail).getByText("tidak ada data")).toBeDefined();
    expect(within(detail).getByText(/tidak ada penilaian risiko untuk wilayah ini/i)).toBeDefined();
  });
});

describe("rincian wilayah", () => {
  const detailProps = {
    horizon: "6H",
    assessmentDate: "2025-12-31",
    weightsVersion: "dummy-v1",
  };

  it("menampilkan potensi ancaman dan jam paling rawan", () => {
    render(<DistrictDetail district={districtOf("Kebayoran Baru") ?? null} {...detailProps} />);

    expect(screen.getByText("CURAT")).toBeDefined();
    expect(screen.getAllByText("CURANMOR").length).toBeGreaterThan(0);
    expect(screen.getAllByText("18:00-23:59").length).toBeGreaterThan(0);
  });

  it("menampilkan WHY lengkap dengan asal faktor RULE/MODEL", () => {
    // CLAUDE.md §27: asal penjelasan tidak boleh disembunyikan.
    render(<DistrictDetail district={districtOf("Kebayoran Baru") ?? null} {...detailProps} />);

    expect(screen.getByText("RULE")).toBeDefined();
    expect(screen.getByText("MODEL")).toBeDefined();
    expect(screen.getByText("Kepadatan kejadian historis")).toBeDefined();
    expect(screen.getByText("38%")).toBeDefined();
    expect(screen.getByText(/kontribusi aturan berbobot/i)).toBeDefined();
  });

  it("menampilkan WHAT/WHEN/RISK/CONFIDENCE prediksi beserta ketertelusurannya", () => {
    render(<DistrictDetail district={districtOf("Kebayoran Baru") ?? null} {...detailProps} />);

    expect(screen.getByText("54")).toBeDefined();
    expect(screen.getByText("63%")).toBeDefined();
    expect(screen.getByText(/PRD-00116/)).toBeDefined();
    expect(screen.getAllByText(/dummy-v1/).length).toBeGreaterThan(0);
  });

  it("menyatakan bila wilayah tidak punya prediksi terpublikasi", () => {
    render(<DistrictDetail district={districtOf("Tebet") ?? null} {...detailProps} />);

    expect(screen.getByText(/tidak ada prediksi terpublikasi/i)).toBeDefined();
  });

  it("meminta pengguna memilih wilayah bila belum ada yang dipilih", () => {
    render(<DistrictDetail district={null} {...detailProps} />);

    expect(screen.getByText(/pilih salah satu kecamatan/i)).toBeDefined();
  });
});
