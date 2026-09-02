import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { byPolsek, locationLabel, referenceDate } from "@/lib/data-entry";
import { CrimeForm } from "./crime-form";
import type { Choice, LocationGroup, TriageReport } from "./options";
import { TriageForm } from "./triage-form";

// Kedua formulir memanggil server action; yang diuji di sini bentuk layarnya.
vi.mock("./actions", () => ({
  recordCrime: vi.fn(),
  recordIntelligence: vi.fn(),
  triageReport: vi.fn(),
}));

const INCIDENT_TYPES: Choice[] = [
  { value: "CURANMOR", label: "Curanmor" },
  { value: "BEGAL", label: "Begal" },
  { value: "UNJUK_RASA", label: "Unjuk Rasa" },
];

const CRIME_STATUSES: Choice[] = [
  { value: "REPORTED", label: "Dilaporkan" },
  { value: "INVESTIGATION", label: "Penyidikan" },
];

const REPORT_STATUSES: Choice[] = [
  { value: "RECEIVED", label: "Diterima" },
  { value: "VERIFIED", label: "Diverifikasi" },
];

const LOCATIONS: LocationGroup[] = [
  {
    polsek: "Polsek Tebet",
    options: [{ value: "LOC-001", label: "Tebet Barat, Tebet · JKS-001" }],
  },
  {
    polsek: "Polsek Setiabudi",
    options: [{ value: "LOC-020", label: "Karet, Setiabudi · JKS-020" }],
  },
];

const REPORTS: TriageReport[] = [
  {
    code: "RPT-0001",
    label: "Keramaian · Tebet Barat, Tebet",
    status: "RECEIVED",
    statusLabel: "Diterima",
  },
];

function crimeForm() {
  return render(
    <CrimeForm
      incidentTypes={INCIDENT_TYPES}
      statuses={CRIME_STATUSES}
      locations={LOCATIONS}
      locationTypes={["Jalan", "Permukiman"]}
      modusOptions={["jambret"]}
      targetTypes={["motor"]}
      maxDate="2025-12-31"
      demoClock
    />,
  );
}

describe("pilihan wilayah", () => {
  it("mengelompokkan sel grid menurut Polsek, berurutan", () => {
    const grouped = byPolsek([
      { ...cell("LOC-020", "Polsek Setiabudi", "Setiabudi", "Karet", "JKS-020") },
      { ...cell("LOC-001", "Polsek Tebet", "Tebet", "Tebet Barat", "JKS-001") },
      { ...cell("LOC-002", "Polsek Tebet", "Tebet", null, "JKS-002") },
    ]);

    expect(grouped.map((group) => group.polsek)).toEqual(["Polsek Setiabudi", "Polsek Tebet"]);
    expect(grouped[1].rows).toHaveLength(2);
  });

  it("menyatakan kelurahan bila ada, dan tidak mengarangnya bila kosong", () => {
    expect(locationLabel(cell("LOC-001", "Polsek Tebet", "Tebet", "Tebet Barat", "JKS-001"))).toBe(
      "Tebet Barat, Tebet · JKS-001",
    );
    expect(locationLabel(cell("LOC-002", "Polsek Tebet", "Tebet", null, "JKS-002"))).toBe(
      "Tebet · JKS-002",
    );
  });
});

describe("batas tanggal", () => {
  it("mengikuti waktu acuan aplikasi dalam WIB, bukan zona peramban", () => {
    // 31 Desember 2025 pukul 21.00 WIB = 14.00 UTC. Dibaca sebagai UTC, tanggalnya tetap
    // 31 Desember; yang membuktikan konversi bekerja adalah waktu yang melewati tengah malam.
    expect(referenceDate("2025-12-31T14:00:00+00:00")).toBe("2025-12-31");
    expect(referenceDate("2025-12-31T18:00:00+00:00")).toBe("2026-01-01");
  });
});

describe("formulir kejadian", () => {
  it("menawarkan seluruh jenis ancaman dari taksonomi", () => {
    crimeForm();

    for (const item of INCIDENT_TYPES) {
      expect(screen.getByRole("option", { name: item.label })).toBeDefined();
    }
  });

  it("membatasi tanggal pada waktu acuan aplikasi", () => {
    crimeForm();

    const field = screen.getByLabelText(/Tanggal Kejadian/i);
    expect(field.getAttribute("max")).toBe("2025-12-31");
  });

  it("menyatakan bahwa identitas orang memang tidak diminta", () => {
    // Ketiadaan isian identitas adalah keputusan (spesifikasi §6.1), bukan kelalaian —
    // dan itu harus terbaca di layar, bukan hanya di kode.
    crimeForm();

    expect(screen.getByText(/tidak meminta identitas korban/i)).toBeDefined();
    expect(screen.queryByLabelText(/korban|pelaku|saksi/i)).toBeNull();
  });

  it("mengelompokkan wilayah menurut Polsek supaya batas cakupan terlihat", () => {
    crimeForm();

    const grouped = screen.getByLabelText(/Wilayah/i).querySelectorAll("optgroup");
    expect([...grouped].map((group) => group.getAttribute("label"))).toEqual([
      "Polsek Tebet",
      "Polsek Setiabudi",
    ]);
  });
});

describe("formulir triase", () => {
  it("menyebut verifikasi sebagai tindakan yang bermakna", () => {
    render(
      <TriageForm
        reports={REPORTS}
        statuses={REPORT_STATUSES}
        verificationBasis="Bobot community_factor kini 0,00 sehingga verifikasi belum menggerakkan risk score."
        transitionBasis="Belum ada SOP triase."
      />,
    );

    expect(screen.getByText(/Verifikasi bukan sekadar label/i)).toBeDefined();
    expect(screen.getByText(/community_factor/)).toBeDefined();
  });

  it("menyatakan keadaan kosong, bukan menampilkan pemilih hampa", () => {
    render(
      <TriageForm
        reports={[]}
        statuses={REPORT_STATUSES}
        verificationBasis="…"
        transitionBasis="…"
      />,
    );

    expect(screen.getByText(/Tidak ada laporan masyarakat dalam cakupan akun Anda/i)).toBeDefined();
    expect(screen.queryByRole("button", { name: /Ubah Status/i })).toBeNull();
  });
});

/** Baris `locations` secukupnya untuk menguji pengelompokan dan pelabelan. */
function cell(
  code: string,
  polsek: string,
  kecamatan: string,
  kelurahan: string | null,
  gridId: string,
) {
  return {
    code,
    grid_id: gridId,
    polsek,
    kecamatan,
    kelurahan,
    latitude: -6.2,
    longitude: 106.8,
    location_type: null,
  };
}
