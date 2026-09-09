import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PredictionRow, RunResult } from "@/lib/prediction-center";
import { contributionText, factorValue, horizonLabel, statusLabel } from "./display";
import { PredictionBoard } from "./prediction-board";
import { RunPanel } from "./run-panel";
import type { PublishState, RunState } from "./run-state";
import { RunSummary } from "./run-summary";

/** Server action digantikan tiruan: yang diuji di sini layarnya, bukan backend-nya. */
const submitRun = vi.fn<(previous: RunState, form: FormData) => Promise<RunState>>();
const submitPublish = vi.fn<(previous: PublishState, form: FormData) => Promise<PublishState>>();

vi.mock("./actions", () => ({
  submitRun: (previous: RunState, form: FormData) => submitRun(previous, form),
  submitPublish: (previous: PublishState, form: FormData) => submitPublish(previous, form),
}));

beforeEach(() => {
  submitRun.mockReset();
  submitPublish.mockReset();
});

/**
 * Uji layar AI Prediction Center.
 *
 * Yang dijaga di sini bukan rupa layarnya melainkan janjinya:
 *
 * 1. setiap prediksi menjawab WHAT, WHERE, WHEN, RISK, CONFIDENCE, dan WHY;
 * 2. layar menyatakan sendiri bahwa **tidak ada model terlatih** di balik angkanya;
 * 3. penjelasan berlabel `RULE`, dan faktor tak terukur ditulis "tidak terukur" — bukan 0;
 * 4. tombol menjalankan dan mempublikasikan disembunyikan dari peran tanpa kewenangan,
 *    beserta sebabnya — dan itu dinyatakan sebagai kenyamanan, bukan pengaman;
 * 5. publikasi hanya ditawarkan atas prediksi berstatus Draf;
 * 6. uji coba mendahului penulisan, dan penolakan backend tampil apa adanya.
 */

const draft: PredictionRow = {
  code: "PRD-00901",
  prediction_date: "2025-12-31",
  forecast_horizon: "24H",
  threat_type: "CURANMOR",
  time_window: "18:00-23:59",
  window_start: "2026-01-01T11:00:00+00:00",
  window_end: "2026-01-01T17:00:00+00:00",
  risk_score: 78,
  confidence: 32,
  dominant_factors: [
    {
      factor: "historical_factor",
      value: 88,
      weight: 0.3,
      contribution: 26.4,
      source: "RULE",
      reason: null,
      basis: null,
    },
    {
      factor: "context_factor",
      value: null,
      weight: null,
      contribution: 0,
      source: "RULE",
      reason: "kategori TKP sel ini kosong",
      basis: null,
    },
    {
      factor: "confidence_support",
      value: 7,
      weight: null,
      contribution: 0,
      source: "RULE",
      reason: "7 kejadian CURANMOR pada sel ini di jendela 18:00-23:59",
      basis: null,
    },
  ],
  model_version: "rule-persistence-v1",
  status: "DRAFT",
  kecamatan: "Kebayoran Baru",
  kelurahan: "Senayan",
  grid_id: "JKS-001",
};

const published: PredictionRow = {
  ...draft,
  code: "PRD-00902",
  status: "PUBLISHED",
  risk_score: 61,
};

const filter = { horizon: null, status: null };

const result: RunResult = {
  prediction_date: "2025-12-31",
  horizon: "24H",
  dry_run: true,
  written: 0,
  existing_rows: 0,
  status_written: "DRAFT",
  target_date: "2026-01-01",
  window_from: "2025-12-31T17:00:00+00:00",
  window_to: "2026-01-01T17:00:00+00:00",
  time_windows: ["00:00-06:00", "06:00-12:00", "12:00-18:00", "18:00-23:59"],
  threat_types: ["CURANMOR", "CURAT"],
  combinations: 660,
  predicted: 656,
  not_predicted: 4,
  reference_time: "2025-12-31T21:00:00+07:00",
  demo_clock: true,
  rule_version: "rule-persistence-v1",
  weights_versions: ["dummy-v1"],
  threshold_version: "dummy-v1",
  threshold_status: "DEMO",
  evidence: { incidents: 1200, date_from: "2023-01-01", date_to: "2025-12-31" },
  not_computed_reason: null,
  baseline_class_distribution: { HIGH: 12, LOW: 644 },
  by_threat_type: [
    { threat_type: "CURANMOR", windows: 132, highest: 88, average: 41, average_confidence: 18 },
  ],
  not_predicted_reasons: [
    { reason: "tidak ada baris risk_scores untuk sel JKS-020, jenis TAWURAN", combinations: 4 },
  ],
  sample: [
    {
      grid_id: "JKS-001",
      kecamatan: "Kebayoran Baru",
      kelurahan: "Senayan",
      polsek: "Polsek Kebayoran Baru",
      threat_type: "CURANMOR",
      time_window: "18:00-23:59",
      window_start: "2026-01-01T11:00:00+00:00",
      window_end: "2026-01-01T17:00:00+00:00",
      risk_score: 88,
      baseline_risk_class: "CRITICAL",
      confidence: 25,
      confidence_reason: "7 kejadian CURANMOR pada sel ini di jendela 18:00-23:59",
      supporting_incidents: 7,
      baseline_code: "RS-01234",
      baseline_assessment_date: "2025-12-18",
      baseline_age_days: 14,
      weights_version: "dummy-v1",
      dominant_factors: [
        {
          factor: "historical_factor",
          value: 100,
          weight: 0.3,
          contribution: 30,
          source: "RULE",
          reason: null,
          basis: null,
        },
        {
          factor: "context_factor",
          value: null,
          weight: null,
          contribution: 0,
          source: "RULE",
          reason: "kategori TKP sel ini kosong",
          basis: null,
        },
      ],
      not_predicted_reason: null,
    },
  ],
  horizon_basis: "Horizon dibaca sebagai PANJANG RENTANG ke depan.",
  projection_basis: "Ini proyeksi persistensi berbasis aturan — BUKAN model terlatih.",
  confidence_basis: "confidence mengukur ketebalan bukti, bukan peluang kejadian.",
  not_predicted_basis:
    "Kombinasi tanpa baris risk_scores pada label jendela yang sama tidak diprediksi.",
  model_disclaimer: "Tidak ada model terlatih di balik angka ini.",
  publication_basis: "Hanya prediksi PUBLISHED yang boleh melahirkan peringatan dini.",
  dry_run_basis: "tidak ada satu baris predictions pun yang ditulis",
  status_basis: "Prediksi baru berstatus DRAFT.",
};

describe("rincian prediksi", () => {
  it("menjawab WHAT, WHERE, WHEN, RISK, CONFIDENCE, dan WHY", () => {
    render(
      <PredictionBoard
        rows={[draft]}
        total={1}
        selected={draft}
        filter={filter}
        canPublish={false}
      />,
    );

    expect(screen.getByText("Apa (WHAT)")).toBeDefined();
    expect(screen.getByText("Di mana (WHERE)")).toBeDefined();
    expect(screen.getByText("Kapan (WHEN)")).toBeDefined();
    expect(screen.getByText("Risiko (RISK)")).toBeDefined();
    expect(screen.getByText("Keyakinan (CONFIDENCE)")).toBeDefined();
    expect(screen.getByText("Mengapa (WHY)")).toBeDefined();
  });

  it("menyatakan sendiri bahwa tidak ada model terlatih di baliknya", () => {
    render(
      <PredictionBoard
        rows={[draft]}
        total={1}
        selected={draft}
        filter={filter}
        canPublish={false}
      />,
    );

    expect(screen.getByText(/tidak ada model terlatih di balik angka ini/i)).toBeDefined();
    expect(screen.getByText("rule-persistence-v1")).toBeDefined();
  });

  it("menandai setiap penjelasan sebagai RULE, dan tidak menulis yang tak terukur sebagai nol", () => {
    render(
      <PredictionBoard
        rows={[draft]}
        total={1}
        selected={draft}
        filter={filter}
        canPublish={false}
      />,
    );

    // Tiga penanda pada ketiga faktor, ditambah satu pada kalimat yang menjelaskan bahwa
    // seluruh faktor berlabel RULE — bukan temuan model.
    expect(screen.getAllByText("RULE")).toHaveLength(4);
    expect(screen.getByText("tidak terukur")).toBeDefined();
    expect(screen.getByText(/kategori TKP sel ini kosong/)).toBeDefined();
  });

  it("membawa dasar keyakinan, bukan hanya angkanya", () => {
    render(
      <PredictionBoard
        rows={[draft]}
        total={1}
        selected={draft}
        filter={filter}
        canPublish={false}
      />,
    );

    expect(screen.getByText(/Dasar keyakinan/)).toBeDefined();
    expect(screen.getByText(/7 kejadian CURANMOR pada sel ini/)).toBeDefined();
  });

  it("menyatakan layar kosong ketika tidak ada prediksi pada penyaring", () => {
    render(
      <PredictionBoard rows={[]} total={0} selected={null} filter={filter} canPublish={false} />,
    );

    expect(screen.getByText(/Tidak ada prediksi pada penyaring ini/)).toBeDefined();
  });
});

describe("publikasi", () => {
  it("menyembunyikan tombol dari peran tanpa kewenangan, dan menyebut sebabnya", () => {
    render(
      <PredictionBoard
        rows={[draft]}
        total={1}
        selected={draft}
        filter={filter}
        canPublish={false}
      />,
    );

    expect(screen.queryByRole("button", { name: /publikasikan/i })).toBeNull();
    expect(screen.getByText(/tidak memiliki kewenangan/)).toBeDefined();
  });

  it("hanya menawarkan publikasi atas prediksi berstatus Draf", () => {
    render(
      <PredictionBoard
        rows={[published]}
        total={1}
        selected={published}
        filter={filter}
        canPublish
      />,
    );

    expect(screen.queryByRole("button", { name: /publikasikan/i })).toBeNull();
    expect(screen.getByText(/Hanya prediksi berstatus Draf/)).toBeDefined();
  });

  it("mengirim kode prediksi yang sedang dibuka", async () => {
    submitPublish.mockResolvedValue({ error: null, published: null });
    render(
      <PredictionBoard rows={[draft]} total={1} selected={draft} filter={filter} canPublish />,
    );

    fireEvent.click(screen.getByRole("button", { name: /publikasikan/i }));

    await waitFor(() => expect(submitPublish).toHaveBeenCalledTimes(1));
    expect(submitPublish.mock.calls[0][1].get("code")).toBe("PRD-00901");
  });

  it("menampilkan penolakan backend apa adanya", async () => {
    submitPublish.mockResolvedValue({
      error: "Prediksi berstatus PUBLISHED tidak dapat dipublikasikan ulang.",
      published: null,
    });
    render(
      <PredictionBoard rows={[draft]} total={1} selected={draft} filter={filter} canPublish />,
    );

    fireEvent.click(screen.getByRole("button", { name: /publikasikan/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain("tidak dapat dipublikasikan ulang"),
    );
  });
});

describe("hasil penjalanan", () => {
  it("menegaskan uji coba tidak menulis apa pun", () => {
    render(<RunSummary result={result} />);

    expect(screen.getByText(/Uji coba/)).toBeDefined();
    expect(screen.getByText(/tidak ada satu baris predictions pun yang ditulis/i)).toBeDefined();
  });

  it("memisahkan yang diprediksi dari yang tidak, beserta alasannya", () => {
    render(<RunSummary result={result} />);

    expect(screen.getByText("Tidak Diprediksi").nextElementSibling?.textContent).toBe("4");
    expect(screen.getByText(/tidak ada baris risk_scores untuk sel JKS-020/)).toBeDefined();
  });

  it("menyebut baris penilaian yang menjadi dasar tiap prediksi contoh", () => {
    render(<RunSummary result={result} />);

    const card = screen.getByText("JKS-001").closest("li");
    expect(card).not.toBeNull();
    const rows = within(card as HTMLElement);
    expect(rows.getByText("RS-01234")).toBeDefined();
    expect(rows.getByText(/14 hari sebelum jendela yang diprediksi/)).toBeDefined();
    expect(rows.getByText("tidak terukur")).toBeDefined();
  });

  it("membawa dasar proyeksi dan keyakinan apa adanya dari API", () => {
    render(<RunSummary result={result} />);

    expect(screen.getByText(/BUKAN model terlatih/)).toBeDefined();
    expect(screen.getByText(/ketebalan bukti, bukan peluang kejadian/)).toBeDefined();
  });
});

describe("tombol penjalanan", () => {
  it("menyembunyikan tombol dari peran tanpa kewenangan, dan menyebut sebabnya", () => {
    render(<RunPanel canRun={false} referenceDate="2025-12-31" />);

    expect(screen.queryByRole("button", { name: /uji coba/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /tulis prediksi/i })).toBeNull();
    expect(screen.getByText(/tidak memiliki kewenangan/)).toBeDefined();
  });

  it("menyatakan bahwa ini bukan keluaran model terlatih", () => {
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    expect(screen.getByText(/bukan keluaran model terlatih/)).toBeDefined();
  });

  it("menyebut horizon sebagai jarak, bukan panjang rentang", () => {
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    expect(screen.getByText(/bukan panjang rentang/)).toBeDefined();
    expect(screen.getByText(/jumlah barisnya sama untuk semua horizon/)).toBeDefined();
  });

  it("menutup tombol tulis sampai ada hasil uji coba", async () => {
    submitRun.mockResolvedValue({ error: null, result: null });
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    const write = screen.getByRole("button", { name: /tulis prediksi/i });
    expect(write.hasAttribute("disabled")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /uji coba/i }));
    await waitFor(() => expect(submitRun).toHaveBeenCalledTimes(1));
    // Uji coba dikirim sebagai mode "uji"; hanya "tulis" yang menulis.
    expect(submitRun.mock.calls[0][1].get("mode")).toBe("uji");
    expect(submitRun.mock.calls[0][1].get("horizon")).toBe("24H");
  });

  it("membuka tombol tulis setelah uji coba horizon yang sama ditampilkan", async () => {
    submitRun.mockResolvedValue({ error: null, result });
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    fireEvent.click(screen.getByRole("button", { name: /uji coba/i }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /tulis prediksi/i }).hasAttribute("disabled")).toBe(
        false,
      ),
    );
    expect(screen.getByText(/Uji coba/)).toBeDefined();
  });

  it("menampilkan penolakan backend apa adanya", async () => {
    submitRun.mockResolvedValue({
      error: "Tanggal prediksi 2025-12-31 dengan horizon 24H sudah memiliki 660 baris predictions.",
      result: null,
    });
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    fireEvent.click(screen.getByRole("button", { name: /uji coba/i }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("660 baris"));
  });
});

describe("pembentukan teks", () => {
  it("membedakan tidak terukur dari nol", () => {
    expect(factorValue(null)).toBe("tidak terukur");
    expect(factorValue(undefined)).toBe("tidak terukur");
    expect(factorValue(0)).toBe("0");
  });

  it("membedakan tidak berbobot dari berbobot nol", () => {
    expect(contributionText(0, null)).toContain("tidak berbobot");
    expect(contributionText(0, 0)).toContain("tidak menyumbang");
    expect(contributionText(30, 0.3)).toContain("30 poin");
  });

  it("tetap menampilkan sumbangan prediksi lama yang tidak menyimpan bobotnya", () => {
    // Prediksi seed membawa contribution tanpa weight; angkanya tidak boleh hilang.
    expect(contributionText(0.312, null)).toContain("0,312 poin");
    expect(contributionText(0.312, null)).toContain("bobot tidak tercatat");
  });

  it("menerjemahkan horizon dan status tanpa mengubah maknanya", () => {
    expect(horizonLabel("7D")).toBe("7 hari");
    expect(horizonLabel("48H")).toBe("48H");
    expect(statusLabel("DRAFT")).toBe("Draf");
    expect(statusLabel("ENTAH")).toBe("ENTAH");
  });
});
