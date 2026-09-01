import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  type DecisionRow,
  indexDecisions,
  type RecommendationRow,
  splitByDecision,
} from "@/lib/decisions";
import { RecommendationBoard } from "./recommendation-board";

// Formulir keputusan memanggil server action; di sini yang diuji papan keputusannya.
vi.mock("./decision-form", () => ({
  DecisionForm: ({ code }: { code: string }) => (
    <button type="button">Catat Keputusan {code}</button>
  ),
}));

const pendingRow: RecommendationRow = {
  code: "REC-0101",
  recommended_function: "SAMAPTA",
  recommendation_text: "Tambah patroli pada jam 18.00–24.00 di Pasar Minggu.",
  priority: "HIGH",
  status: "PENDING_REVIEW",
  created_at: "2025-12-27T02:30:00+00:00",
  prediction_code: "PRD-00035",
  warning_code: "WRN-0053",
};

const decidedRow: RecommendationRow = {
  ...pendingRow,
  code: "REC-0102",
  status: "MODIFIED",
  recommendation_text: "Kerahkan dua unit ke Tebet.",
};

const decision: DecisionRow = {
  code: "DEC-0064",
  decision: "MODIFIED",
  reason: "Satu unit sedang menangani kejadian lain.",
  modified_text: "Kerahkan satu unit ke Tebet, satu unit siaga di Mapolsek.",
  decided_at: "2025-12-27T03:00:00+00:00",
  recommendation_code: "REC-0102",
  recommended_function: "SAMAPTA",
  original_recommendation: "Kerahkan dua unit ke Tebet.",
  kecamatan: "Tebet",
};

/**
 * Kueri dibatasi pada satu panel, bukan seluruh layar: teks yang sama memang muncul di
 * kartu daftar dan di panel rincian, dan yang diuji adalah letaknya.
 */
function panel(title: string) {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
}

const detail = () => panel("Usulan Sistem & Keputusan");
const list = () => panel("Rekomendasi Tindakan");

function board(props: Partial<Parameters<typeof RecommendationBoard>[0]> = {}) {
  return render(
    <RecommendationBoard
      pending={[pendingRow]}
      decided={[decidedRow]}
      selected={pendingRow}
      decision={null}
      canDecide
      {...props}
    />,
  );
}

describe("pembagian rekomendasi", () => {
  it("memisahkan yang menunggu keputusan dari yang sudah diputus", () => {
    const { pending, decided } = splitByDecision([pendingRow, decidedRow]);

    expect(pending.map((row) => row.code)).toEqual(["REC-0101"]);
    expect(decided.map((row) => row.code)).toEqual(["REC-0102"]);
  });

  it("menautkan keputusan ke rekomendasinya", () => {
    expect(indexDecisions([decision]).get("REC-0102")?.code).toBe("DEC-0064");
  });
});

describe("papan rekomendasi", () => {
  it("menampilkan kedua kelompok beserta jumlahnya", () => {
    board();

    expect(list().getByRole("heading", { name: /Menunggu Keputusan \(1\)/ })).toBeDefined();
    expect(list().getByRole("heading", { name: /Sudah Diputus \(1\)/ })).toBeDefined();
  });

  it("menyatakan rekomendasi sebagai opsi, bukan perintah", () => {
    // CLAUDE.md §13–§14: rantai human-in-the-loop harus terbaca di layar.
    board();

    expect(screen.getByText(/opsi, bukan perintah/i)).toBeDefined();
  });

  it("menampilkan usulan sistem beserta prediksi sumbernya", () => {
    board();

    expect(detail().getByText(/Tambah patroli pada jam/)).toBeDefined();
    expect(detail().getByRole("link", { name: "PRD-00035" })).toBeDefined();
  });

  it("membuka formulir keputusan bagi pejabat berwenang", () => {
    board();

    expect(screen.getByRole("button", { name: /Catat Keputusan REC-0101/ })).toBeDefined();
  });

  it("menyembunyikan formulir bagi peran tanpa kewenangan", () => {
    board({ canDecide: false });

    expect(screen.queryByRole("button", { name: /Catat Keputusan/ })).toBeNull();
    expect(screen.getByText(/tidak memiliki kewenangan memutuskan/i)).toBeDefined();
  });

  it("menyandingkan usulan asli dengan hasil modifikasi pejabat", () => {
    // U-07: keputusan manusia tidak menimpa usulan sistem; keduanya harus terlihat.
    board({ selected: decidedRow, decision });

    expect(detail().getByText("Kerahkan dua unit ke Tebet.")).toBeDefined();
    expect(detail().getByText(/satu unit siaga di Mapolsek/)).toBeDefined();
    expect(detail().getByText(/sedang menangani kejadian lain/)).toBeDefined();
  });

  it("menyatakan keadaan kosong, bukan menampilkan panel hampa", () => {
    board({ pending: [], decided: [], selected: null });

    expect(list().getByText(/Tidak ada rekomendasi yang menunggu keputusan/i)).toBeDefined();
    expect(screen.getByText(/Pilih satu rekomendasi/i)).toBeDefined();
  });

  it("tidak menawarkan keputusan atas rekomendasi yang sudah diputus", () => {
    board({ selected: decidedRow, decision });

    expect(screen.queryByRole("button", { name: /Catat Keputusan/ })).toBeNull();
  });
});
