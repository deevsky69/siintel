import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  effectiveOrder,
  type OperationRow,
  type PendingDecisionRow,
  splitByProgress,
  unitOptions,
  wibIso,
} from "@/lib/operations";
import { OperationBoard } from "./operation-board";

// Kedua formulir memanggil server action; di sini yang diuji papan operasinya.
vi.mock("./assignment-form", () => ({
  AssignmentForm: ({ decisionCode }: { decisionCode: string }) => (
    <button type="button">Catat Penugasan {decisionCode}</button>
  ),
}));
vi.mock("./result-form", () => ({
  ResultForm: ({ code }: { code: string }) => (
    <button type="button">Catat Hasil Nyata {code}</button>
  ),
}));

const queued: PendingDecisionRow = {
  decision_code: "DEC-0086",
  decision: "APPROVED",
  decision_at: "2025-12-27T02:00:00+00:00",
  recommendation_code: "REC-0007",
  recommended_function: "BINMAS",
  original_recommendation: "Tambah kegiatan preventif di Pancoran pada jam rawan.",
  modified_text: null,
  priority: "MEDIUM",
  kecamatan: "Pancoran",
  polsek: "Polsek Pancoran",
};

const running: OperationRow = {
  code: "ACT-0015",
  status: "ACTIVE",
  start_at: "2025-12-25T04:00:00+00:00",
  end_at: null,
  result: "Penugasan sedang berjalan.",
  unit_code: "UNIT-003",
  unit_name: "Unit Patroli Charlie",
  unit_function: "SAMAPTA",
  kecamatan: "Kebayoran Baru",
  kelurahan: "Cipete Utara",
  polsek: "Polsek Kebayoran Baru",
  decision_code: "DEC-0031",
  decision: "MODIFIED",
  decision_at: "2025-12-25T02:00:00+00:00",
  recommendation_code: "REC-0031",
  recommended_function: "LANTAS",
  original_recommendation: "Kerahkan dua unit ke Cipete Utara.",
  modified_text: "Kerahkan satu unit ke Cipete Utara, satu unit siaga di Mapolsek.",
};

const finished: OperationRow = {
  ...running,
  code: "ACT-0038",
  status: "COMPLETED",
  end_at: "2025-12-25T10:00:00+00:00",
  result: "Kegiatan preventif terlaksana; tidak ada kejadian menonjol.",
  unit_code: "UNIT-005",
  unit_name: "Unit Monitoring Wilayah",
  unit_function: "INTELKAM",
  decision: "APPROVED",
  modified_text: null,
};

/**
 * Kueri dibatasi pada satu panel: perintah yang sama memang muncul di kartu daftar dan
 * di panel rincian, dan yang diuji adalah letaknya — pola yang sama dengan
 * `rekomendasi/recommendations.test.tsx`.
 */
function panel(title: string) {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
}

const detail = () => panel("Rincian Penugasan");
const list = () => panel("Antrean & Tindakan Operasional");

function board(props: Partial<Parameters<typeof OperationBoard>[0]> = {}) {
  return render(
    <OperationBoard
      queue={[queued]}
      awaitingResult={[running]}
      withResult={[finished]}
      selectedDecision={queued}
      selectedAction={null}
      units={[{ code: "UNIT-003", name: "Unit Patroli Charlie", function: "SAMAPTA" }]}
      canWrite
      {...props}
    />,
  );
}

describe("perintah yang berlaku", () => {
  it("memakai teks pejabat bila keputusannya dimodifikasi", () => {
    // U-07: keputusan manusia yang dijalankan, bukan usulan mentah sistem.
    expect(effectiveOrder(running)).toEqual({
      text: "Kerahkan satu unit ke Cipete Utara, satu unit siaga di Mapolsek.",
      adjusted: true,
    });
  });

  it("memakai usulan asli bila keputusannya menyetujui apa adanya", () => {
    expect(effectiveOrder(finished).adjusted).toBe(false);
    expect(effectiveOrder(finished).text).toBe("Kerahkan dua unit ke Cipete Utara.");
  });

  it("tidak menganggap teks modifikasi kosong sebagai perintah", () => {
    const row = { ...running, modified_text: "   " };

    expect(effectiveOrder(row).text).toBe("Kerahkan dua unit ke Cipete Utara.");
  });
});

describe("pembagian tindakan", () => {
  it("memisahkan yang hasilnya belum tercatat dari yang sudah", () => {
    const { awaitingResult, withResult } = splitByProgress([running, finished]);

    expect(awaitingResult.map((row) => row.code)).toEqual(["ACT-0015"]);
    expect(withResult.map((row) => row.code)).toEqual(["ACT-0038"]);
  });

  it("memperlakukan pembatalan sebagai hasil yang sudah tercatat", () => {
    const cancelled = { ...running, code: "ACT-0099", status: "CANCELLED" };

    expect(splitByProgress([cancelled]).withResult).toHaveLength(1);
  });
});

describe("daftar satuan", () => {
  it("dikumpulkan unik dari tindakan yang pernah tercatat", () => {
    // Belum ada endpoint data induk satuan; daftar tidak boleh ditanam di kode.
    expect(unitOptions([running, finished, running])).toEqual([
      { code: "UNIT-003", name: "Unit Patroli Charlie", function: "SAMAPTA" },
      { code: "UNIT-005", name: "Unit Monitoring Wilayah", function: "INTELKAM" },
    ]);
  });

  it("kosong bila belum ada tindakan sama sekali", () => {
    expect(unitOptions([])).toEqual([]);
  });
});

describe("waktu isian formulir", () => {
  it("menyatakan zona WIB secara eksplisit", () => {
    // Kolom waktu bertipe timestamptz; waktu tanpa zona ditolak backend.
    expect(wibIso("2025-12-27T14:30")).toBe("2025-12-27T14:30:00+07:00");
    expect(wibIso("2025-12-27T14:30:45")).toBe("2025-12-27T14:30:45+07:00");
  });

  it("menolak isian yang tidak dapat dibaca, bukan mengarang waktu", () => {
    expect(wibIso("")).toBeNull();
    expect(wibIso("27/12/2025 14:30")).toBeNull();
  });
});

describe("papan operasi", () => {
  it("menampilkan ketiga kelompok beserta jumlahnya", () => {
    board();

    expect(
      list().getByRole("heading", { name: /Sudah Diputus, Belum Ditindaklanjuti \(1\)/ }),
    ).toBeDefined();
    expect(
      list().getByRole("heading", { name: /Berjalan, Hasil Belum Tercatat \(1\)/ }),
    ).toBeDefined();
    expect(list().getByRole("heading", { name: /Hasil Sudah Tercatat \(1\)/ })).toBeDefined();
  });

  it("menyatakan keputusan yang belum dijalankan sebagai keadaan yang menganga", () => {
    // Inti layar ini: "sudah diputus tetapi tidak pernah dijalankan" harus terlihat.
    board();

    expect(detail().getByText(/belum ditindaklanjuti/i)).toBeDefined();
    expect(detail().getByText(/belum ada hasil nyata yang dapat dievaluasi/i)).toBeDefined();
  });

  it("membuka formulir penugasan bagi peran berwenang", () => {
    board();

    expect(screen.getByRole("button", { name: /Catat Penugasan DEC-0086/ })).toBeDefined();
  });

  it("menyembunyikan formulir penugasan bagi peran tanpa kewenangan", () => {
    board({ canWrite: false });

    expect(screen.queryByRole("button", { name: /Catat Penugasan/ })).toBeNull();
    expect(detail().getByText(/tidak memiliki kewenangan mencatat penugasan/i)).toBeDefined();
  });

  it("menyandingkan perintah yang berlaku dengan usulan asli sistem", () => {
    board({ selectedDecision: null, selectedAction: running });

    expect(detail().getByText(/satu unit siaga di Mapolsek/)).toBeDefined();
    expect(detail().getByText("Kerahkan dua unit ke Cipete Utara.")).toBeDefined();
    expect(detail().getByText(/Pejabat menyesuaikan usulan sistem/i)).toBeDefined();
  });

  it("membedakan catatan rencana dari hasil nyata", () => {
    board({ selectedDecision: null, selectedAction: running });

    expect(detail().getByText("Catatan Penugasan")).toBeDefined();
    expect(detail().getByText(/Ini catatan rencana, bukan hasil/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /Catat Hasil Nyata ACT-0015/ })).toBeDefined();
  });

  it("tidak menawarkan pencatatan hasil atas tindakan yang sudah final", () => {
    board({ selectedDecision: null, selectedAction: finished });

    expect(detail().getByText("Hasil Nyata")).toBeDefined();
    expect(screen.queryByRole("button", { name: /Catat Hasil Nyata/ })).toBeNull();
    expect(detail().getByText(/tidak dapat diubah dari layar ini/i)).toBeDefined();
  });

  it("menyatakan keadaan kosong, bukan menampilkan panel hampa", () => {
    board({
      queue: [],
      awaitingResult: [],
      withResult: [],
      selectedDecision: null,
      selectedAction: null,
    });

    expect(
      list().getByText(/Seluruh keputusan yang disetujui sudah ditindaklanjuti/i),
    ).toBeDefined();
    expect(screen.getByText(/Pilih satu keputusan atau tindakan/i)).toBeDefined();
  });
});
