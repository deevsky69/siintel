import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { IntelligencePage, IntelligenceRow } from "@/lib/intel";
import {
  areaOf,
  formatDate,
  intelligenceHref,
  labelOf,
  pageRangeText,
  readSelection,
  scoreText,
  selectReport,
  toggled,
} from "./display";
import { ReportBoard } from "./report-board";

/**
 * Uji layar Laporan Intelijen.
 *
 * Yang dijaga bukan rupa layarnya melainkan janjinya: keadaan layar tersimpan di URL,
 * penilaian pada laporan tidak pernah tampil seolah berasal dari mesin, jumlah pada
 * penyaring dinyatakan penyebutnya, dan keadaan kosong dijelaskan dengan kalimat.
 */

const rows: IntelligenceRow[] = [
  {
    code: "INT-0068",
    report_date: "2025-12-31",
    category: "Gangguan Kamtibmas",
    reliability: "A",
    confidence: 78,
    urgency: 88,
    impact: "HIGH",
    status: "VERIFIED",
    location_code: "LOC-031",
    kecamatan: "Jagakarsa",
    kelurahan: "Ciganjur",
    polsek: "Polsek Jagakarsa",
    grid_id: "JKS-031",
  },
  {
    code: "INT-0042",
    report_date: "2025-11-02",
    category: "Potensi Tawuran",
    reliability: "C",
    confidence: null,
    urgency: null,
    impact: null,
    status: "NEW",
    location_code: "LOC-020",
    kecamatan: "Tebet",
    kelurahan: null,
    polsek: "Polsek Tebet",
    grid_id: "JKS-020",
  },
];

const ASSESSMENT_BASIS =
  "reliability (A/B/C), confidence (0-100), dan urgency (0-100) adalah penilaian yang DICATAT PADA LAPORAN oleh pelapor/penyusunnya — bukan keluaran model dan bukan hitungan sistem.";

const FILTER_BASIS =
  "Jumlah pada tiap pilihan penyaring dihitung atas SELURUH laporan dalam cakupan Anda, bukan atas hasil penyaringan yang sedang tampil.";

const page: IntelligencePage = {
  data: rows,
  pagination: { page: 1, page_size: 25, total_items: 121, total_pages: 5 },
  filters: {
    status: [
      { value: "CLOSED", reports: 31 },
      { value: "VERIFIED", reports: 30 },
      { value: "NEW", reports: 29 },
    ],
    category: [
      { value: "Kerawanan Lokasi", reports: 33 },
      { value: "Potensi Tawuran", reports: 29 },
    ],
    reliability: [{ value: "A", reports: 68 }],
  },
  source: { table: "intelligence_reports", reports_in_scope: 121, scope: null },
  scope_basis: "Seluruh laporan di wilayah Polres dapat Anda lihat.",
  filter_basis: FILTER_BASIS,
  assessment_basis: ASSESSMENT_BASIS,
};

const selection = { status: null, category: null, page: 1, selected: null };

function renderBoard(overrides: Partial<Parameters<typeof ReportBoard>[0]> = {}) {
  return render(
    <ReportBoard page={page} selection={selection} selected={rows[0]} {...overrides} />,
  );
}

/** Kueri dibatasi pada satu panel: label yang sama muncul di daftar dan di rincian. */
function panel(title: string | RegExp) {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
}

describe("keadaan layar dari alamat", () => {
  it("membaca penyaring, halaman, dan laporan terpilih", () => {
    expect(
      readSelection({
        status: "verified",
        kategori: "Potensi Tawuran",
        halaman: "3",
        dipilih: "INT-0042",
      }),
    ).toEqual({ status: "VERIFIED", category: "Potensi Tawuran", page: 3, selected: "INT-0042" });
  });

  it("mengembalikan halaman tak masuk akal ke halaman pertama", () => {
    // Tautan usang tidak boleh berakhir sebagai galat backend di tengah paparan.
    expect(readSelection({ halaman: "0" }).page).toBe(1);
    expect(readSelection({ halaman: "-4" }).page).toBe(1);
    expect(readSelection({ halaman: "bukan-angka" }).page).toBe(1);
    expect(readSelection({}).page).toBe(1);
  });

  it("mengabaikan parameter ganda yang bukan teks tunggal", () => {
    expect(readSelection({ status: ["NEW", "CLOSED"] }).status).toBeNull();
  });
});

describe("tautan keadaan layar", () => {
  it("menyusun alamat dari penyaring yang berlaku", () => {
    expect(intelligenceHref(selection, { status: "NEW" })).toBe("/intelijen?status=NEW");
    expect(intelligenceHref(selection, {})).toBe("/intelijen");
  });

  it("mengembalikan ke halaman pertama dan melepas laporan saat penyaring berubah", () => {
    // Laporan yang sedang dibuka bisa saja tidak lagi termasuk hasil penyaringan.
    const current = { status: null, category: null, page: 4, selected: "INT-0068" };

    expect(intelligenceHref(current, { status: "CLOSED" })).toBe("/intelijen?status=CLOSED");
  });

  it("mempertahankan penyaring saat berpindah halaman", () => {
    const current = { status: "NEW", category: null, page: 1, selected: null };

    expect(intelligenceHref(current, { page: 2 })).toBe("/intelijen?status=NEW&halaman=2");
  });

  it("melepas penyaring bila nilai yang sama dipilih lagi", () => {
    expect(toggled("NEW", "NEW")).toBeNull();
    expect(toggled("NEW", "CLOSED")).toBe("CLOSED");
  });
});

describe("pemformatan nilai", () => {
  it("selalu menyebut skala di samping angka penilaian", () => {
    expect(scoreText(78)).toBe("78/100");
  });

  it("membedakan tidak dicatat dari bernilai nol", () => {
    expect(scoreText(null)).toBe("—");
    expect(scoreText(0)).toBe("0/100");
  });

  it("menyebut wilayah selengkap yang tercatat", () => {
    expect(areaOf(rows[0])).toBe("Jagakarsa — Ciganjur");
    expect(areaOf(rows[1])).toBe("Tebet");
  });

  it("memakai nilai mentah bila belum ada padanan Indonesianya", () => {
    expect(labelOf({ NEW: "Baru" }, "NEW")).toBe("Baru");
    expect(labelOf({ NEW: "Baru" }, "BELUM_ADA")).toBe("BELUM_ADA");
    expect(labelOf({ NEW: "Baru" }, null)).toBe("Tidak dicatat");
  });

  it("menyebut cakupan halaman beserta jumlah seluruhnya", () => {
    expect(pageRangeText(1, 25, 121)).toBe("laporan 1–25 dari 121");
    expect(pageRangeText(5, 25, 121)).toBe("laporan 101–121 dari 121");
    expect(pageRangeText(1, 25, 0)).toBe("tidak ada laporan yang cocok");
  });

  it("merapikan tanggal laporan", () => {
    const expected = new Date("2025-12-31").toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    expect(formatDate("2025-12-31")).toBe(expected);
  });
});

describe("pemilihan laporan", () => {
  it("membuka laporan yang diminta", () => {
    expect(selectReport(rows, "INT-0042")?.code).toBe("INT-0042");
  });

  it("jatuh ke laporan pertama bila tautannya usang", () => {
    expect(selectReport(rows, "INT-9999")?.code).toBe("INT-0068");
  });

  it("tidak memilih apa pun bila daftarnya kosong", () => {
    expect(selectReport([], "INT-0068")).toBeNull();
  });
});

describe("layar Laporan Intelijen", () => {
  it("menampilkan daftar laporan beserta wilayah dan tahapannya", () => {
    renderBoard();

    const list = panel("Daftar");
    expect(list.getByText("Gangguan Kamtibmas")).toBeDefined();
    expect(list.getByText("Potensi Tawuran")).toBeDefined();
    expect(list.getByText("Jagakarsa — Ciganjur")).toBeDefined();
  });

  it("menyatakan bahwa penilaian pada laporan bukan keluaran model", () => {
    renderBoard();

    // Ini yang membedakan `confidence` di sini dari `confidence` milik prediksi.
    expect(screen.getByText(/bukan keluaran model/)).toBeDefined();
  });

  it("menampilkan rincian laporan yang dipilih", () => {
    renderBoard();

    const detail = panel("Rincian Laporan");
    expect(detail.getByText("78/100")).toBeDefined();
    expect(detail.getByText("88/100")).toBeDefined();
    expect(detail.getByText("Sumber terpercaya")).toBeDefined();
    expect(detail.getByText(/Dampak Tinggi/)).toBeDefined();
  });

  it("menulis nilai yang tidak dicatat sebagai '—', bukan sebagai nol", () => {
    renderBoard({ selected: rows[1] });

    const detail = panel("Rincian Laporan");
    expect(detail.getAllByText("—").length).toBe(2);
    expect(detail.queryByText("0/100")).toBeNull();
  });

  it("menyebut penyebut jumlah pada penyaring", () => {
    renderBoard();

    expect(screen.getByText(/SELURUH laporan dalam cakupan Anda/)).toBeDefined();
  });

  it("menandai penyaring yang sedang aktif", () => {
    renderBoard({ selection: { ...selection, status: "NEW" } });

    // Dibatasi pada panel penyaring: kartu laporan yang sedang dibuka juga membawa
    // `aria-current`, dan keduanya memang menandai hal yang berbeda.
    const active = panel("Laporan Intelijen").getByRole("link", { current: true });
    expect(active.textContent).toContain("Baru");
  });

  it("menjelaskan keadaan kosong akibat penyaring, bukan menampilkan daftar hampa", () => {
    renderBoard({
      page: {
        ...page,
        data: [],
        pagination: { ...page.pagination, total_items: 0, total_pages: 0 },
      },
      selection: { ...selection, status: "CLOSED" },
      selected: null,
    });

    expect(screen.getByText(/Lepaskan salah satu penyaring/)).toBeDefined();
  });

  it("membedakan kosong karena kewenangan dari kosong karena penyaring", () => {
    renderBoard({
      page: {
        ...page,
        data: [],
        pagination: { ...page.pagination, total_items: 0, total_pages: 0 },
      },
      selected: null,
    });

    expect(screen.getByText(/kewenangan Anda/)).toBeDefined();
  });

  it("menyediakan penelusuran halaman ketika laporannya lebih dari satu halaman", () => {
    renderBoard({ selection: { ...selection, page: 2 } });

    expect(screen.getByRole("link", { name: /Sebelumnya/ })).toBeDefined();
    expect(screen.getByRole("link", { name: /Berikutnya/ })).toBeDefined();
  });

  it("tidak menampilkan skor risiko maupun prediksi", () => {
    renderBoard();

    expect(screen.queryByText(/skor risiko/i)).toBeNull();
    expect(screen.queryByText(/prediksi/i)).toBeNull();
  });
});
