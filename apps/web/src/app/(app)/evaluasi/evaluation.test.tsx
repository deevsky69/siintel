import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EvaluationMetrics, EvaluationSummary } from "@/lib/evaluation";
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
