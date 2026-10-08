import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EvaluationMetrics, EvaluationSummary, RecommendationOutcome } from "@/lib/evaluation";
import { formatPercent, formatRatio } from "@/lib/evaluation";
import { EvaluationView } from "./evaluation-view";

const BASIS =
  "Cakupan: kejadian nyata pada periode prediksi untuk jenis ancaman yang diprediksi " +
  "(CURANMOR, CURAT, CURAS). Aturan pencocokan final belum ditetapkan (U-03).";

const metrics: EvaluationMetrics = {
  hits: 60,
  false_positives: 91,
  false_negatives: 90,
  precision: 0.397,
  recall: 0.4,
  evaluated_rows: 241,
  status: "PROPOSED",
  basis: BASIS,
};

const summary: EvaluationSummary = {
  per_threat: {
    CURANMOR: { HIT: 39, FALSE_NEGATIVE: 40 },
    CURAT: { HIT: 11, FALSE_NEGATIVE: 32 },
    "TIDAK DIKETAHUI": { FALSE_POSITIVE: 91 },
  },
  model_versions: ["dummy-v1"],
  status: "PROPOSED",
  basis: BASIS,
};

describe("evaluation center", () => {
  it("menampilkan metrik yang diterima dari API", () => {
    render(<EvaluationView metrics={metrics} summary={summary} />);

    expect(screen.getByText("0,397")).toBeDefined();
    expect(screen.getByText("0,400")).toBeDefined();
    expect(screen.getByText("60")).toBeDefined();
    expect(screen.getAllByText("91").length).toBeGreaterThan(0);
    expect(screen.getAllByText("90").length).toBeGreaterThan(0);
    expect(screen.getAllByText("241").length).toBeGreaterThan(0);
  });

  it("menampilkan penanda status dan dasar perhitungan dari API", () => {
    // CLAUDE.md §26 dan U-03: angka evaluasi tidak boleh tampil seolah final.
    render(<EvaluationView metrics={metrics} summary={summary} />);

    expect(screen.getByText("PROPOSED")).toBeDefined();
    expect(screen.getByText(/U-03/)).toBeDefined();
    expect(screen.getByText(/belum final/i)).toBeDefined();
  });

  it("merinci hasil per jenis ancaman", () => {
    render(<EvaluationView metrics={metrics} summary={summary} />);

    expect(screen.getByText("CURANMOR")).toBeDefined();
    expect(screen.getByText("CURAT")).toBeDefined();
    expect(screen.getByText("TIDAK DIKETAHUI")).toBeDefined();
    expect(screen.getByText(/versi model dummy-v1/i)).toBeDefined();
  });

  it("menjelaskan arti precision dan recall bagi pembaca non-teknis", () => {
    render(<EvaluationView metrics={metrics} summary={summary} />);

    expect(screen.getByText(/berapa bagian yang benar-benar terbukti/i)).toBeDefined();
    expect(screen.getByText(/banyak kejadian lolos tanpa/i)).toBeDefined();
  });

  it("menyatakan keadaan kosong dengan kata, bukan angka nol", () => {
    render(
      <EvaluationView
        metrics={{
          ...metrics,
          hits: 0,
          false_positives: 0,
          false_negatives: 0,
          precision: null,
          recall: null,
          evaluated_rows: 0,
        }}
        summary={{ ...summary, per_threat: {}, model_versions: [] }}
      />,
    );

    expect(screen.getByText("Tidak ada baris evaluasi yang tercatat.")).toBeDefined();
    expect(screen.getByText("Tidak ada rincian per jenis ancaman.")).toBeDefined();
    expect(screen.getByText("tidak ada baris dievaluasi")).toBeDefined();
  });
});

const outcome: RecommendationOutcome = {
  target_years: [2026],
  observed_to: "2026-09-28",
  rows: [
    {
      code: "REC-0007",
      status: "PENDING_REVIEW",
      priority: "HIGH",
      recommended_function: "SAMAPTA",
      prediction_code: "PRD-0007",
      threat_type: "CURANMOR",
      kecamatan: "Cilandak",
      kelurahan: "Cipete Utara",
      time_window: "00:00-06:00",
      window_start: "2025-12-31T17:00:00+00:00",
      window_end: "2025-12-31T22:59:00+00:00",
      risk_score: 75,
      target_year: 2026,
      literal_window_hit: false,
      area_incidents: 21,
      area_timed_incidents: 14,
      area_unknown_time: 7,
      block_incidents: 6,
      block_share_percent: 42.9,
      expected_share_percent: 25,
      area_rank: 1,
      area_rank_of: 58,
      verdict: "SEJALAN",
    },
    {
      code: "REC-0008",
      status: "PENDING_REVIEW",
      priority: "HIGH",
      recommended_function: "SAMAPTA",
      prediction_code: "PRD-0008",
      threat_type: "CURANMOR",
      kecamatan: "Cilandak",
      kelurahan: "Cipete Utara",
      time_window: "06:00-12:00",
      window_start: "2025-12-31T17:00:00+00:00",
      window_end: "2025-12-31T22:59:00+00:00",
      risk_score: 75,
      target_year: 2026,
      literal_window_hit: false,
      area_incidents: 21,
      area_timed_incidents: 14,
      area_unknown_time: 7,
      block_incidents: 1,
      block_share_percent: 7.1,
      expected_share_percent: 25,
      area_rank: 1,
      area_rank_of: 58,
      verdict: "SEBAGIAN",
    },
  ],
  summary: {
    total: 2,
    aligned: 1,
    partial: 1,
    not_aligned: 0,
    unevaluable: 0,
    literal_window_hits: 0,
    aligned_percent: 50,
  },
  status: "PROPOSED",
  basis: "Aturan ini PROPOSED (U-03).",
};

describe("rekomendasi vs kenyataan", () => {
  it("menampilkan putusan per rekomendasi beserta angka yang mendasarinya", () => {
    render(<EvaluationView metrics={metrics} summary={summary} outcome={outcome} />);

    expect(screen.getByRole("heading", { name: /Rekomendasi vs Kenyataan 2026/ })).toBeDefined();
    expect(screen.getByText("1 dari 2")).toBeDefined();
    // Label kartu ringkasan dan tanda putusan per baris memakai kata yang sama.
    expect(screen.getAllByText("Sejalan").length).toBe(2);
    expect(screen.getAllByText("Sebagian").length).toBe(2);
    expect(screen.getByText("6 dari 14")).toBeDefined();
    expect(screen.getByText(/42,9% vs 25%/)).toBeDefined();
    expect(screen.getAllByText("1 dari 58").length).toBe(2);
  });

  it("menyebut jendela harfiah yang kosong, bukan menyembunyikannya", () => {
    render(<EvaluationView metrics={metrics} summary={summary} outcome={outcome} />);

    expect(screen.getByText("0 dari 2")).toBeDefined();
    expect(screen.getByText(/hampir selalu kosong/i)).toBeDefined();
  });

  it("menyatakan panel tidak termuat tanpa menjatuhkan angka lain", () => {
    render(<EvaluationView metrics={metrics} summary={summary} outcome={null} />);

    expect(screen.getByText(/Pencocokan rekomendasi tidak termuat/)).toBeDefined();
    expect(screen.getByText("0,397")).toBeDefined();
  });

  it("menyatakan keadaan kosong dengan kata", () => {
    render(
      <EvaluationView
        metrics={metrics}
        summary={summary}
        outcome={{ ...outcome, rows: [], summary: { ...outcome.summary, total: 0 } }}
      />,
    );

    expect(screen.getByText(/Belum ada rekomendasi yang dapat dicocokkan/)).toBeDefined();
  });
});

describe("format angka evaluasi", () => {
  it("membedakan nilai nol dari nilai yang tidak dapat dihitung", () => {
    expect(formatRatio(0)).toBe("0,000");
    expect(formatRatio(null)).toBe("tidak dapat dihitung");
  });

  it("menyediakan bentuk persen untuk pembaca non-teknis", () => {
    expect(formatPercent(0.397)).toBe("39,7%");
    expect(formatPercent(null)).toBeNull();
  });
});
