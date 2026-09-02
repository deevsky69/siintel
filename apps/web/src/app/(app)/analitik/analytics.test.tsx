import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SpatialPatternResponse, TimePatternResponse, TrendResponse } from "@/lib/analytics";
import { AnalyticsView } from "./analytics-view";
import {
  analyticsHref,
  decimalText,
  HEAT_CLASSES,
  heatLevel,
  isReversedRange,
  linePath,
  monthTicks,
  peakOfSeries,
  readSelection,
  seriesColor,
  toggledThreatType,
} from "./display";

/**
 * Uji layar Crime Analytics.
 *
 * Yang dijaga bukan rupa layarnya melainkan janjinya: keadaan layar tersimpan di URL,
 * persentase tidak pernah tampil tanpa penyebutnya, skala gambar dinyatakan sebagai skala
 * (bukan sebagai ambang), tidak ada kalimat yang menjadikan sebaran masa lalu terbaca
 * sebagai prediksi, dan bedanya dengan Crime Pattern DNA terbaca lebih dulu.
 */

const ANALYSIS_BASIS =
  "Seluruh angka pada layar analitik adalah jumlah kejadian yang SUDAH TERJADI pada tabel crime_incidents — bukan prediksi, bukan skor risiko.";

const RELATED_BASIS =
  "Layar ini membandingkan jenis gangguan satu sama lain. Profil mendalam SATU jenis ada pada Crime Pattern DNA (GET /analytics/crime-pattern-dna).";

const SOURCE = {
  table: "crime_incidents",
  date_from: "2023-01-01",
  date_to: "2025-12-31",
  incidents: 1202,
  scope: null,
};

const months = [
  { key: "2025-01", label: "Jan 2025", year: 2025, month: 1, incidents: 40, share_percent: 40.0 },
  { key: "2025-02", label: "Feb 2025", year: 2025, month: 2, incidents: 35, share_percent: 35.0 },
  { key: "2025-03", label: "Mar 2025", year: 2025, month: 3, incidents: 25, share_percent: 25.0 },
];

const trend: TrendResponse = {
  threat_type: null,
  threat_types: [
    { threat_type: "CURANMOR", incidents: 465 },
    { threat_type: "CURAT", incidents: 282 },
  ],
  months,
  series: [
    {
      threat_type: "CURANMOR",
      incidents: 60,
      share_percent: 60.0,
      monthly: [25, 20, 15],
    },
    { threat_type: "CURAT", incidents: 40, share_percent: 40.0, monthly: [15, 15, 10] },
  ],
  incidents: 100,
  denominator: 100,
  months_counted: 3,
  peak_month: { key: "2025-01", incidents: 40 },
  mean_per_month: 33.3,
  mean_basis: "Rata-rata = 100 kejadian dibagi 3 bulan pada sumbu, termasuk bulan tanpa kejadian.",
  peak_basis: "Bulan terbanyak adalah nilai maksimum aritmetika, bukan penanda menonjol.",
  source: SOURCE,
  scope_basis: "Seluruh angka dihitung dari kejadian di seluruh wilayah Polres.",
  analysis_basis: ANALYSIS_BASIS,
  related_analysis_basis: RELATED_BASIS,
};

const DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];

const pattern: TimePatternResponse = {
  threat_type: null,
  threat_types: trend.threat_types,
  days: DAY_NAMES.map((label, index) => ({
    day: index + 1,
    label,
    incidents: index === 6 ? 21 : 0,
    share_percent: index === 6 ? 21.0 : 0,
    cells: Array.from({ length: 24 }, (_, hour) => ({
      hour,
      label: `${String(hour).padStart(2, "0")}.00`,
      incidents: index === 6 && hour === 18 ? 21 : 0,
      share_percent: index === 6 && hour === 18 ? 21.0 : 0,
    })),
  })),
  hours: Array.from({ length: 24 }, (_, hour) => ({
    hour,
    label: `${String(hour).padStart(2, "0")}.00`,
    incidents: hour === 18 ? 21 : 0,
    share_percent: hour === 18 ? 21.0 : 0,
  })),
  incidents: 100,
  denominator: 100,
  cells: 168,
  peak_cell: {
    day: 7,
    day_label: "Minggu",
    hour: 18,
    label: "Minggu 18.00",
    incidents: 21,
    share_percent: 21.0,
  },
  cell_basis:
    "Matriks ini memiliki 168 sel yang berbagi 100 kejadian; bila tersebar rata, tiap sel berisi 0.6 kejadian. Angka itu pembanding aritmetika, bukan ambang.",
  time_basis: "Jam diambil dari kolom incident_time — waktu setempat (WIB).",
  source: SOURCE,
  scope_basis: trend.scope_basis,
  analysis_basis: ANALYSIS_BASIS,
  related_analysis_basis: RELATED_BASIS,
};

const spatial: SpatialPatternResponse = {
  threat_types: [
    { threat_type: "CURANMOR", incidents: 60, share_percent: 60.0 },
    { threat_type: "CURAT", incidents: 40, share_percent: 40.0 },
  ],
  areas: [
    {
      kecamatan: "Kebayoran Baru",
      polsek: "Polsek Kebayoran Baru",
      incidents: 70,
      share_percent: 70.0,
      denominator: 70,
      by_threat: [
        {
          threat_type: "CURANMOR",
          incidents: 42,
          share_of_area_percent: 60.0,
          share_of_threat_percent: 70.0,
        },
        {
          threat_type: "CURAT",
          incidents: 28,
          share_of_area_percent: 40.0,
          share_of_threat_percent: 70.0,
        },
      ],
    },
    {
      kecamatan: "Tebet",
      polsek: "Polsek Tebet",
      incidents: 30,
      share_percent: 30.0,
      denominator: 30,
      by_threat: [
        {
          threat_type: "CURANMOR",
          incidents: 18,
          share_of_area_percent: 60.0,
          share_of_threat_percent: 30.0,
        },
        {
          threat_type: "CURAT",
          incidents: 12,
          share_of_area_percent: 40.0,
          share_of_threat_percent: 30.0,
        },
      ],
    },
  ],
  incidents: 100,
  denominator: 100,
  areas_compared: 2,
  share_basis:
    "share_of_area_percent memakai jumlah kejadian kecamatan itu sendiri; share_of_threat_percent memakai jumlah kejadian jenis itu di seluruh cakupan.",
  comparison_basis: "Perbandingan ini mencakup 2 kecamatan di wilayah Polres.",
  rate_basis:
    "Perbandingan antarwilayah ini memakai JUMLAH kejadian, bukan angka per penduduk maupun per luas wilayah.",
  source: SOURCE,
  scope_basis: trend.scope_basis,
  analysis_basis: ANALYSIS_BASIS,
  related_analysis_basis: RELATED_BASIS,
};

const selection = { threatType: null, dateFrom: null, dateTo: null };

function renderView(overrides: Partial<Parameters<typeof AnalyticsView>[0]> = {}) {
  return render(
    <AnalyticsView
      selection={selection}
      trend={trend}
      pattern={pattern}
      spatial={spatial}
      {...overrides}
    />,
  );
}

/** Kueri dibatasi pada satu panel: nama jenis yang sama muncul di beberapa panel. */
function panel(title: string | RegExp) {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
}

describe("keadaan layar dari alamat", () => {
  it("membaca jenis dan rentang tanggal", () => {
    expect(readSelection({ jenis: "curanmor", dari: "2025-01-01", sampai: "2025-06-30" })).toEqual({
      threatType: "CURANMOR",
      dateFrom: "2025-01-01",
      dateTo: "2025-06-30",
    });
  });

  it("mengabaikan tanggal yang tidak berbentuk YYYY-MM-DD", () => {
    // Tautan usang tidak boleh menjatuhkan halaman ke layar galat di tengah paparan.
    expect(readSelection({ dari: "kemarin" }).dateFrom).toBeNull();
    expect(readSelection({ sampai: "2025-13" }).dateTo).toBeNull();
  });

  it("mengenali rentang yang terbalik", () => {
    expect(
      isReversedRange({ threatType: null, dateFrom: "2025-06-01", dateTo: "2025-01-01" }),
    ).toBe(true);
    expect(
      isReversedRange({ threatType: null, dateFrom: "2025-01-01", dateTo: "2025-06-01" }),
    ).toBe(false);
    expect(isReversedRange(selection)).toBe(false);
  });

  it("menyusun tautan keadaan layar", () => {
    expect(analyticsHref(selection, { threatType: "CURANMOR" })).toBe("/analitik?jenis=CURANMOR");
    expect(analyticsHref(selection, { dateFrom: "2025-01-01" })).toBe("/analitik?dari=2025-01-01");
    expect(analyticsHref(selection, {})).toBe("/analitik");
  });

  it("kembali ke seluruh jenis bila jenis yang sama dipilih lagi", () => {
    expect(toggledThreatType("CURANMOR", "CURANMOR")).toBeNull();
    expect(toggledThreatType("CURANMOR", "CURAT")).toBe("CURAT");
  });
});

describe("penskalaan gambar", () => {
  it("memberi sel tanpa kejadian tingkat warna tersendiri", () => {
    // Nol harus terlihat berbeda dari "sedikit"; keduanya bukan hal yang sama.
    expect(heatLevel(0, 21)).toBe(0);
    expect(heatLevel(1, 21)).toBe(1);
  });

  it("menskalakan warna terhadap sel terbanyak, bukan terhadap ambang", () => {
    expect(heatLevel(21, 21)).toBe(HEAT_CLASSES.length - 1);
    expect(heatLevel(11, 21)).toBe(3);
  });

  it("tidak pernah keluar dari daftar kelas yang benar-benar ditulis", () => {
    for (const incidents of [0, 1, 7, 13, 20, 21]) {
      expect(HEAT_CLASSES[heatLevel(incidents, 21)]).toBeDefined();
    }
  });

  it("memberi label sumbu bulan cukup jarang, dengan bulan terakhir selalu ikut", () => {
    expect(monthTicks(36, 6)).toEqual([0, 6, 12, 18, 24, 30, 35]);
    expect(monthTicks(3, 6)).toEqual([0, 2]);
    expect(monthTicks(0, 6)).toEqual([]);
  });

  it("menggambar garis tren sendiri, tanpa pustaka grafik", () => {
    expect(linePath([0, 10], 10, 100, 50)).toBe("M0.0,50.0 L100.0,0.0");
    expect(linePath([], 10, 100, 50)).toBe("");
  });

  it("menskalakan garis terhadap deret tertinggi", () => {
    expect(peakOfSeries(trend.series)).toBe(25);
  });

  it("memutar warna deret bila jenisnya lebih banyak dari paletnya", () => {
    expect(seriesColor(0)).toBe(seriesColor(6));
  });

  it("menulis desimal dengan koma", () => {
    expect(decimalText(33.3)).toBe("33,3");
  });
});

describe("layar Crime Analytics", () => {
  it("menyatakan bedanya dengan Crime Pattern DNA dan menautkannya", () => {
    renderView();

    expect(screen.getByText(/Profil mendalam SATU jenis/)).toBeDefined();
    expect(screen.getByRole("link", { name: /Buka Crime Pattern DNA/ })).toBeDefined();
  });

  it("menyatakan bahwa ini bukan prediksi", () => {
    renderView();

    expect(screen.getByText(/bukan prediksi/)).toBeDefined();
    expect(screen.queryByText(/tingkat keyakinan/i)).toBeNull();
  });

  it("menampilkan keempat analisis yang diminta spesifikasi", () => {
    renderView();

    for (const title of [
      "Tren Bulanan",
      "Distribusi Jenis",
      "Hari & Jam Rawan",
      "Perbandingan Antarwilayah",
    ]) {
      expect(screen.getByRole("heading", { name: title })).toBeDefined();
    }
  });

  it("tidak pernah menulis persentase tanpa penyebutnya", () => {
    renderView();

    expect(panel("Distribusi Jenis").getByText("60,0% dari 100 kejadian")).toBeDefined();
    expect(panel("Perbandingan Antarwilayah").getByText(/70,0% dari 100 kejadian/)).toBeDefined();
  });

  it("menyatakan skala gambar sebagai skala, bukan sebagai ambang", () => {
    renderView();

    expect(panel("Tren Bulanan").getByText(/relatif terhadap bulan terbanyak/)).toBeDefined();
    expect(panel("Hari & Jam Rawan").getByText(/bukan terhadap ambang/)).toBeDefined();
  });

  it("menggambar matriks tujuh hari x dua puluh empat jam", () => {
    renderView();

    const rows = panel("Hari & Jam Rawan").getAllByRole("row");
    // Satu baris kepala + tujuh hari.
    expect(rows.length).toBe(8);
    for (const day of DAY_NAMES) {
      expect(panel("Hari & Jam Rawan").getByRole("rowheader", { name: day })).toBeDefined();
    }
  });

  it("menyebut sel terbanyak sebagai fakta, beserta penyebutnya", () => {
    renderView();

    const matrix = panel("Hari & Jam Rawan");
    expect(matrix.getByText(/Minggu 18.00/)).toBeDefined();
    // Kalimat puncaknya sendiri yang diperiksa: persentase yang sama juga muncul pada
    // daftar angka per jam, dan keduanya memang menyebut sel yang sama.
    expect(matrix.getByText(/Sel terbanyak/).textContent).toContain("21,0% dari 100 kejadian");
  });

  it("mengakui bahwa perbandingan wilayah memakai jumlah mentah", () => {
    renderView();

    expect(screen.getByText(/bukan angka per penduduk/)).toBeDefined();
  });

  it("menjelaskan dua penyebut berbeda pada matriks wilayah", () => {
    renderView();

    expect(screen.getByText(/share_of_area_percent memakai/)).toBeDefined();
  });

  it("menyatakan bahwa penyaring jenis tidak berlaku bagi perbandingan wilayah", () => {
    renderView({ selection: { ...selection, threatType: "CURANMOR" } });

    expect(screen.getByText(/tetap menampilkan seluruh jenis/)).toBeDefined();
  });

  it("menjelaskan keadaan kosong dengan kalimat, bukan grafik hampa", () => {
    renderView({
      trend: { ...trend, incidents: 0, months: [], series: [], months_counted: 0 },
      pattern: { ...pattern, incidents: 0 },
      spatial: { ...spatial, areas: [], incidents: 0, areas_compared: 0 },
    });

    expect(panel("Tren Bulanan").getByText(/tidak ada tren untuk digambar/)).toBeDefined();
    expect(panel("Hari & Jam Rawan").getByText(/matriks hari × jam kosong/)).toBeDefined();
    expect(
      panel("Perbandingan Antarwilayah").getByText(/tidak ada wilayah untuk dibandingkan/),
    ).toBeDefined();
  });

  it("menandai jenis gangguan yang sedang disaring", () => {
    renderView({ selection: { ...selection, threatType: "CURAT" } });

    const active = panel("Crime Analytics").getByRole("link", { current: true });
    expect(active.textContent).toContain("Curat");
  });
});
