import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  allowsTransition,
  formatWib,
  type PredictionDetail,
  type WarningAction,
  type WarningDetail,
} from "@/lib/warnings";
import { ExplainabilityPanel } from "./explainability";
import { WarningBoard, type WarningGroup } from "./warning-board";

/**
 * Formulir tindak lanjut memanggil server action; di sini yang diuji adalah papan
 * peringatan — termasuk tombol mana yang **ditawarkan** kepada formulir itu.
 */
vi.mock("./follow-up-form", () => ({
  FollowUpForm: ({ code, offers }: { code: string; offers: WarningAction[] }) => (
    <div>
      {offers.map((action) => (
        <button key={action} type="button">
          Tindak Lanjut {action} {code}
        </button>
      ))}
    </div>
  ),
}));

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
  threshold_status: "FINAL",
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

const resolved: WarningDetail = {
  ...active,
  code: "WRN-0080",
  status: "RESOLVED",
};

const groups: WarningGroup[] = [
  { status: "ACTIVE", rows: [active], total: 41 },
  { status: "ACKNOWLEDGED", rows: [acknowledged], total: 1 },
  { status: "RESOLVED", rows: [], total: 0 },
];

/**
 * Kueri dibatasi pada satu panel, bukan seluruh layar: teks yang sama memang muncul di
 * kartu daftar dan di panel rincian, dan yang diuji adalah letaknya.
 */
function panel(title: string) {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
}

const followUp = () => panel("Tindak Lanjut");

function board(props: Partial<Parameters<typeof WarningBoard>[0]> = {}) {
  return render(
    <WarningBoard
      groups={groups}
      selected={active}
      sourcePrediction={prediction}
      canAcknowledge
      canResolve
      {...props}
    />,
  );
}

describe("papan peringatan", () => {
  it("mengelompokkan peringatan menurut status", () => {
    board();

    expect(screen.getByText(/Peringatan Aktif/i)).toBeDefined();
    expect(screen.getByText(/Peringatan Sudah Diterima/i)).toBeDefined();
    expect(screen.getByText(/Peringatan Selesai/i)).toBeDefined();
  });

  it("menampilkan isi kartu peringatan sesuai data API", () => {
    board();

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
    board();

    expect(screen.getByText("Waspada")).toBeDefined();
  });

  it("menyatakan keadaan kosong dengan kata, bukan angka nol", () => {
    board();

    expect(screen.getByText("Tidak ada peringatan berstatus Selesai.")).toBeDefined();
    expect(screen.getByText("tidak ada")).toBeDefined();
  });

  it("menyebut versi ambang beserta statusnya yang sebenarnya", () => {
    // Status dibaca dari barisnya, tidak ditulis tetap di layar. Sampai 9 September 2026
    // kalimat ini berbunyi "DEMO / PROPOSED" apa adanya, sehingga ia tidak ikut berubah
    // ketika ambangnya ditetapkan — dan tidak ada satu test pun yang gagal karenanya.
    board();

    expect(screen.getByText("FINAL")).toBeDefined();
    expect(screen.getAllByText("dummy-v1").length).toBeGreaterThan(0);
    expect(screen.getByText(/sudah ditetapkan pemilik proyek/i)).toBeDefined();
    // Ditetapkan BUKAN berarti terbukti tepat (CLAUDE.md §18).
    expect(screen.getByText(/hanya dapat dinyatakan lewat evaluasi/i)).toBeDefined();
  });

  it("kembali menandai ambang belum final ketika versinya memang belum ditetapkan", () => {
    // Penjaga arah sebaliknya: layar harus ikut berubah bila kelak versi PROPOSED
    // dinyalakan, tanpa satu baris kode pun disunting.
    board({
      groups: [
        {
          status: "ACTIVE",
          rows: [{ ...active, threshold_status: "PROPOSED" }],
          total: 1,
        },
      ],
    });

    expect(screen.getByText("PROPOSED")).toBeDefined();
    expect(screen.getByText(/belum ditetapkan secara resmi/i)).toBeDefined();
  });

  it("menandai peringatan yang sedang dipilih pada tautannya", () => {
    board();

    const link = screen.getByRole("link", { name: /WRN-0053/ });
    expect(link.getAttribute("aria-current")).toBe("true");
    expect(link.getAttribute("href")).toBe("/peringatan?dipilih=WRN-0053");
  });

  it("menyatakan peringatan mana yang sedang ditindaklanjuti", () => {
    board();

    expect(followUp().getByText("WRN-0053")).toBeDefined();
    expect(followUp().getByText("Aktif")).toBeDefined();
  });

  it("menyatakan peringatan bukan perintah operasional", () => {
    // CLAUDE.md §13.
    board();

    expect(screen.getByText(/hanya lahir setelah keputusan pejabat berwenang/i)).toBeDefined();
  });
});

describe("kesahan transisi peringatan", () => {
  // Cerminan `ACKNOWLEDGEABLE_FROM` dan `RESOLVABLE_FROM` pada `warning_actions.py`.
  it("hanya mengizinkan acknowledge dari status aktif", () => {
    expect(allowsTransition("ACTIVE", "acknowledge")).toBe(true);
    expect(allowsTransition("ACKNOWLEDGED", "acknowledge")).toBe(false);
    expect(allowsTransition("RESOLVED", "acknowledge")).toBe(false);
  });

  it("mengizinkan resolve dari status aktif maupun sudah diterima", () => {
    expect(allowsTransition("ACTIVE", "resolve")).toBe(true);
    expect(allowsTransition("ACKNOWLEDGED", "resolve")).toBe(true);
    expect(allowsTransition("RESOLVED", "resolve")).toBe(false);
  });
});

describe("panel tindak lanjut", () => {
  it("menawarkan kedua tindak lanjut atas peringatan aktif bagi peran berwenang penuh", () => {
    board();

    expect(followUp().getByRole("button", { name: /acknowledge WRN-0053/ })).toBeDefined();
    expect(followUp().getByRole("button", { name: /resolve WRN-0053/ })).toBeDefined();
  });

  it("tidak menawarkan penutupan bagi peran tanpa kewenangan itu", () => {
    // Role Polsek memiliki `warning:acknowledge` tetapi tidak `warning:resolve`.
    board({ canResolve: false });

    expect(followUp().getByRole("button", { name: /acknowledge WRN-0053/ })).toBeDefined();
    expect(followUp().queryByRole("button", { name: /resolve/ })).toBeNull();
  });

  it("tidak menawarkan penerimaan ulang atas peringatan yang sudah diterima", () => {
    // Menerima ulang akan dijawab 409; tombolnya tidak pantas ditawarkan.
    board({ selected: acknowledged });

    expect(followUp().queryByRole("button", { name: /acknowledge/ })).toBeNull();
    expect(followUp().getByRole("button", { name: /resolve WRN-0017/ })).toBeDefined();
  });

  it("tidak menawarkan tindak lanjut apa pun atas peringatan berstatus akhir", () => {
    board({ selected: resolved });

    expect(followUp().queryByRole("button", { name: /Tindak Lanjut/ })).toBeNull();
    expect(followUp().getByText(/sudah berstatus akhir/i)).toBeDefined();
  });

  it("menyembunyikan tombol bagi peran tanpa kewenangan, sambil menyebut backend yang menolak", () => {
    // CLAUDE.md §21: menyembunyikan tombol bukan pengganti pemeriksaan di backend.
    board({ canAcknowledge: false, canResolve: false });

    expect(followUp().queryByRole("button", { name: /Tindak Lanjut/ })).toBeNull();
    expect(followUp().getByText(/tidak memiliki kewenangan/i)).toBeDefined();
    expect(followUp().getByText(/backend yang menolaknya/i)).toBeDefined();
  });

  it("menyatakan keadaan kosong bila tidak ada peringatan yang dipilih", () => {
    board({ selected: null });

    expect(followUp().getByText(/Tidak ada peringatan yang dipilih/i)).toBeDefined();
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
