import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { historicalOpacity, toHistoricalMonths, toRiskClass } from "@/components/map/area";
import { DistrictDetail } from "@/components/map/district-detail";
import { RiskLegend, riskBands } from "@/components/map/legend";
import { RiskMap } from "@/components/map/risk-map";
import { isWithinMap, KECAMATAN_SHAPES, projectLatLon } from "@/lib/geo";
import type {
  AreaDetail,
  CurrentRiskResponse,
  HistoricalResponse,
  MapData,
  PredictiveResponse,
} from "@/lib/map-data";
import { buildMapData, resolveSelectedDistrict } from "@/lib/map-data";

/**
 * Peta membaca `/map/*`, yang sudah mengagregasi di backend. Uji di bawah karena itu
 * bekerja dari **bentuk respons API**, bukan dari baris mentah `/risk-scores`: yang
 * diperiksa adalah bahwa antarmuka meneruskan kelas, keterangan asal angka, dan keadaan
 * "tidak ada data" apa adanya — bukan menghitung ulang salah satunya.
 */

const CURRENT_BASIS = "Nilai per kecamatan adalah hasil agregasi sel grid di lapisan API.";
const PREDICTIVE_BASIS = "Prediksi tidak menyimpan kelas risiko dan tidak diberi kelas di sini.";

const currentRisk: CurrentRiskResponse = {
  reference_time: "2025-12-27T09:30:00+07:00",
  demo_clock: true,
  assessment_date: "2025-12-31",
  aggregation_basis: CURRENT_BASIS,
  areas: [
    {
      kecamatan: "Kebayoran Baru",
      polsek: "Polsek Kebayoran Baru",
      risk_score: 88,
      risk_class: "CRITICAL",
      average_risk_score: 54,
      cell_count: 20,
      grid_count: 5,
      weights_version: "dummy-v1",
      latitude: -6.24,
      longitude: 106.79,
      threats: [
        {
          threat_type: "CURAT",
          risk_score: 88,
          risk_class: "CRITICAL",
          time_window: "18:00-23:59",
          cell_count: 10,
        },
        {
          threat_type: "CURANMOR",
          risk_score: 71,
          risk_class: "HIGH",
          time_window: "12:00-18:00",
          cell_count: 4,
        },
      ],
    },
    {
      kecamatan: "Tebet",
      polsek: "Polsek Tebet",
      risk_score: 30,
      risk_class: "LOW",
      average_risk_score: 22,
      cell_count: 16,
      grid_count: 4,
      weights_version: "dummy-v1",
      latitude: -6.23,
      longitude: 106.85,
      threats: [
        {
          threat_type: "CURAS",
          risk_score: 30,
          risk_class: "LOW",
          time_window: "00:00-06:00",
          cell_count: 4,
        },
      ],
    },
  ],
};

const predictive: PredictiveResponse = {
  reference_time: "2025-12-27T09:30:00+07:00",
  demo_clock: true,
  horizon: "6H",
  aggregation_basis: PREDICTIVE_BASIS,
  areas: [
    {
      kecamatan: "Kebayoran Baru",
      polsek: "Polsek Kebayoran Baru",
      risk_score: 54,
      confidence: 63,
      threat_type: "CURANMOR",
      time_window: "18:00-23:59",
      window_start: "2025-12-29T11:00:00Z",
      window_end: "2025-12-29T17:00:00Z",
      prediction_code: "PRD-00116",
      model_version: "dummy-v1",
      cell_count: 2,
      threats: [
        {
          threat_type: "CURANMOR",
          risk_score: 54,
          confidence: 63,
          time_window: "18:00-23:59",
          cell_count: 2,
        },
      ],
    },
  ],
};

const areaDetail: AreaDetail = {
  reference_time: "2025-12-27T09:30:00+07:00",
  demo_clock: true,
  kecamatan: "Kebayoran Baru",
  polsek: "Polsek Kebayoran Baru",
  grid_count: 5,
  weights_version: "dummy-v1",
  assessment_date: "2025-12-31",
  threats: currentRisk.areas[0].threats,
  critical_time_window: "18:00-23:59",
  time_windows: [
    { time_window: "18:00-23:59", risk_score: 88, risk_class: "CRITICAL" },
    { time_window: "12:00-18:00", risk_score: 71, risk_class: "HIGH" },
  ],
  top_predictions: [
    {
      code: "PRD-00116",
      threat_type: "CURANMOR",
      kecamatan: "Kebayoran Baru",
      kelurahan: "Senayan",
      grid_id: "JKS-001",
      latitude: -6.24,
      longitude: 106.79,
      time_window: "18:00-23:59",
      window_start: "2025-12-29T11:00:00Z",
      window_end: "2025-12-29T17:00:00Z",
      prediction_date: "2025-12-30",
      forecast_horizon: "6H",
      risk_score: 54,
      confidence: 63,
      dominant_factors: [
        { factor: "historical_incident_density", source: "RULE", contribution: 0.378 },
        { factor: "recent_incident_trend", source: "MODEL", contribution: 0.185 },
      ],
      model_version: "dummy-v1",
      status: "PUBLISHED",
    },
  ],
  history: {
    total_incidents: 160,
    date_from: "2023-01-12",
    date_to: "2025-12-16",
    by_threat_type: [
      { threat_type: "CURANMOR", incidents: 66 },
      { threat_type: "CURAT", incidents: 31 },
    ],
  },
  active_warnings: [
    {
      code: "WRN-0069",
      severity: "CRITICAL",
      threat_type: "CURANMOR",
      time_window: "18:00-23:59",
      window_start: "2025-12-22T11:00:00Z",
      window_end: "2025-12-22T17:00:00Z",
      risk_score: 91,
      confidence: 98,
      status: "ACTIVE",
      grid_id: "JKS-013",
      prediction_code: "PRD-00148",
      threshold_version: "dummy-v1",
    },
  ],
  aggregation_basis: CURRENT_BASIS,
  time_window_basis: "Jendela paling rawan dihitung di lapisan API, bukan tersimpan.",
  active_warnings_basis: "Hanya peringatan berstatus ACTIVE.",
};

const HISTORICAL_BASIS =
  "Angka per kecamatan adalah cacah kejadian mentah pada jendela waktu terpilih, bukan skor risiko.";

const historical: HistoricalResponse = {
  reference_time: "2025-12-27T09:30:00+07:00",
  demo_clock: true,
  months: 12,
  window_from: "2024-12-28",
  window_to: "2025-12-27",
  observed_from: "2025-01-03",
  observed_to: "2025-12-24",
  total_incidents: 260,
  aggregation_basis: HISTORICAL_BASIS,
  areas: [
    {
      kecamatan: "Kebayoran Baru",
      polsek: "Polsek Kebayoran Baru",
      incidents: 180,
      by_threat_type: [
        { threat_type: "CURANMOR", incidents: 120 },
        { threat_type: "CURAT", incidents: 60 },
      ],
    },
    {
      kecamatan: "Tebet",
      polsek: "Polsek Tebet",
      incidents: 80,
      by_threat_type: [{ threat_type: "BEGAL", incidents: 80 }],
    },
  ],
  points: [
    {
      location_code: "LOC-001",
      kecamatan: "Kebayoran Baru",
      kelurahan: "Gunung",
      latitude: -6.227,
      longitude: 106.8,
      incidents: 100,
      dominant_threat_type: "CURANMOR",
    },
    {
      location_code: "LOC-021",
      kecamatan: "Tebet",
      kelurahan: "Tebet Barat",
      latitude: -6.23,
      longitude: 106.855,
      incidents: 40,
      dominant_threat_type: "BEGAL",
    },
    {
      // Sengaja di luar bentang Jakarta Selatan: titik seperti ini tidak boleh dijepitkan
      // ke tepi peta, sebab menjepitkan menaruhnya di wilayah yang bukan wilayahnya.
      location_code: "LOC-999",
      kecamatan: "Kebayoran Baru",
      kelurahan: null,
      latitude: -5.0,
      longitude: 110.0,
      incidents: 5,
      dominant_threat_type: null,
    },
  ],
};

const data: MapData = buildMapData(currentRisk, predictive, historical);
const districtOf = (kecamatan: string) =>
  data.districts.find((row) => row.kecamatan === kecamatan) ?? null;

describe("penyusunan data peta", () => {
  it("menyertakan seluruh kecamatan pada peta, termasuk yang tanpa data", () => {
    expect(data.districts).toHaveLength(KECAMATAN_SHAPES.length);

    const kosong = districtOf("Cilandak");
    expect(kosong?.current).toBeNull();
    expect(kosong?.predictive).toBeNull();
  });

  it("meneruskan skor dan kelas dari API tanpa menghitung ulang", () => {
    const kebayoran = districtOf("Kebayoran Baru");

    expect(kebayoran?.current?.risk_score).toBe(88);
    expect(kebayoran?.current?.risk_class).toBe("CRITICAL");
    expect(kebayoran?.current?.average_risk_score).toBe(54);
    expect(kebayoran?.current?.threats.map((row) => row.threat_type)).toEqual([
      "CURAT",
      "CURANMOR",
    ]);
  });

  it("memasangkan layer prediktif pada kecamatannya sendiri", () => {
    expect(districtOf("Kebayoran Baru")?.predictive?.risk_score).toBe(54);
    expect(districtOf("Tebet")?.predictive).toBeNull();
  });

  it("membawa keterangan asal angka dari kedua endpoint", () => {
    expect(data.currentRiskBasis).toBe(CURRENT_BASIS);
    expect(data.predictiveBasis).toBe(PREDICTIVE_BASIS);
    expect(data.horizon).toBe("6H");
    expect(data.assessmentDate).toBe("2025-12-31");
  });

  it("tidak menurunkan kelas risiko dari skor untuk nilai yang tidak dikenal", () => {
    // CLAUDE.md §12: ambang hanya boleh hidup di satu tempat, yaitu backend.
    expect(toRiskClass("CRITICAL")).toBe("CRITICAL");
    expect(toRiskClass("SANGAT_TINGGI")).toBeNull();
    expect(toRiskClass(null)).toBeNull();
  });
});

describe("pemilihan wilayah lewat alamat", () => {
  it("mempertahankan wilayah yang diminta bila dikenal peta", () => {
    expect(resolveSelectedDistrict(data, "Tebet")).toBe("Tebet");
  });

  it("mempertahankan wilayah dikenal meski tanpa data, bukan melompat ke wilayah lain", () => {
    expect(resolveSelectedDistrict(data, "Cilandak")).toBe("Cilandak");
  });

  it("jatuh ke wilayah berisiko tertinggi bila wilayah tidak dikenal", () => {
    expect(resolveSelectedDistrict(data, "Bandung")).toBe("Kebayoran Baru");
    expect(resolveSelectedDistrict(data, null)).toBe("Kebayoran Baru");
  });

  it("menjawab null bila tidak ada wilayah berdata sama sekali", () => {
    const kosong = buildMapData(
      { ...currentRisk, assessment_date: null, areas: [] },
      { ...predictive, areas: [] },
      {
        ...historical,
        areas: [],
        points: [],
        total_incidents: 0,
        observed_from: null,
        observed_to: null,
      },
    );

    expect(resolveSelectedDistrict(kosong, null)).toBeNull();
  });
});

describe("legenda peta", () => {
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

  it("menyatakan layer prediktif adalah skor mentah tanpa kelas resmi", () => {
    render(<RiskLegend layer="predictive" />);

    expect(screen.getByText(/tanpa kelas risiko resmi/i)).toBeDefined();
    expect(screen.queryByText(/demo \/ proposed/i)).toBeNull();
  });
});

describe("peta risiko", () => {
  const mapProps = {
    data,
    selected: "Kebayoran Baru",
    detail: areaDetail,
    layer: "current" as const,
    months: 12 as const,
  };

  it("menggambar seluruh kecamatan sebagai tautan yang dapat dibagikan", () => {
    render(<RiskMap {...mapProps} />);

    const areas = screen.getAllByRole("link", { name: /—/ });
    expect(areas).toHaveLength(KECAMATAN_SHAPES.length);
    expect(screen.getByRole("link", { name: /^Tebet —/ }).getAttribute("href")).toBe(
      "/peta?wilayah=Tebet",
    );
  });

  it("memberi label wilayah berisi skor dan kelas risikonya", () => {
    render(<RiskMap {...mapProps} />);

    expect(
      screen.getByRole("link", {
        name: "Kebayoran Baru — skor risiko 88 dari 100, kelas Kritis",
      }),
    ).toBeDefined();
  });

  it("menyatakan wilayah tanpa data sebagai tidak ada data, bukan nol", () => {
    render(<RiskMap {...mapProps} />);

    expect(screen.getByRole("link", { name: "Cilandak — tidak ada data risiko" })).toBeDefined();
    expect(screen.queryByLabelText(/Cilandak — skor risiko 0/)).toBeNull();
  });

  it("menandai wilayah terpilih sebagai wilayah berjalan", () => {
    render(<RiskMap {...mapProps} />);

    expect(
      screen.getByRole("link", { name: /^Kebayoran Baru —/ }).getAttribute("aria-current"),
    ).toBe("true");
    expect(screen.getByRole("link", { name: /^Tebet —/ }).getAttribute("aria-current")).toBeNull();
  });

  it("menampilkan tooltip ringkas saat wilayah disentuh tetikus", () => {
    render(<RiskMap {...mapProps} />);

    fireEvent.mouseOver(screen.getByRole("link", { name: /^Tebet —/ }));

    expect(screen.getByText("30/100 · Rendah")).toBeDefined();
  });

  it("menutup tooltip ketika tetikus meninggalkan wilayah", () => {
    render(<RiskMap {...mapProps} />);
    const tebet = screen.getByRole("link", { name: /^Tebet —/ });

    fireEvent.mouseOver(tebet);
    fireEvent.mouseOut(tebet);

    expect(screen.queryByText("30/100 · Rendah")).toBeNull();
  });

  it("menautkan pemilih layer ke alamat, bukan menyimpannya di komponen", () => {
    render(<RiskMap {...mapProps} />);

    expect(screen.getByRole("link", { name: "Prediktif" }).getAttribute("href")).toBe(
      "/peta?wilayah=Kebayoran+Baru&layer=predictive",
    );
    expect(screen.getByRole("link", { name: "Risiko Berjalan" }).getAttribute("href")).toBe(
      "/peta?wilayah=Kebayoran+Baru",
    );
  });

  it("tidak memberi kelas risiko pada layer prediktif", () => {
    // U-01: prediksi tidak membawa `risk_class`, jadi peta tidak boleh mengarangnya.
    render(<RiskMap {...mapProps} layer="predictive" />);

    expect(
      screen.getByRole("link", {
        name: "Kebayoran Baru — skor prediksi 54 dari 100, tanpa kelas risiko",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Tebet — tidak ada prediksi" }).getAttribute("href"),
    ).toBe("/peta?wilayah=Tebet&layer=predictive");
    expect(screen.getByText(/tanpa kelas risiko resmi/i)).toBeDefined();
  });

  it("menampilkan keterangan asal angka milik layer yang sedang tampil", () => {
    const { unmount } = render(<RiskMap {...mapProps} />);
    expect(screen.getAllByText(CURRENT_BASIS).length).toBeGreaterThan(0);
    expect(screen.queryByText(PREDICTIVE_BASIS)).toBeNull();
    unmount();

    render(<RiskMap {...mapProps} layer="predictive" />);
    expect(screen.getByText(PREDICTIVE_BASIS)).toBeDefined();
  });

  it("membuka rincian wilayah yang dipilih alamat", () => {
    render(<RiskMap {...mapProps} />);
    const detail = screen.getByRole("region", { name: /rincian wilayah terpilih/i });

    expect(within(detail).getByText("Kebayoran Baru")).toBeDefined();
    expect(within(detail).getAllByText("88").length).toBeGreaterThan(0);
  });
});

describe("rincian wilayah", () => {
  const kebayoran = districtOf("Kebayoran Baru");

  it("menampilkan potensi ancaman dan jendela paling rawan", () => {
    render(<DistrictDetail district={kebayoran} detail={areaDetail} horizon="6H" />);

    expect(screen.getAllByText("CURAT").length).toBeGreaterThan(0);
    expect(screen.getAllByText("CURANMOR").length).toBeGreaterThan(0);
    expect(screen.getAllByText("18:00-23:59").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Kritis").length).toBeGreaterThan(0);
  });

  it("menampilkan riwayat kejadian historis wilayah beserta rentang datanya", () => {
    render(<DistrictDetail district={kebayoran} detail={areaDetail} horizon="6H" />);

    expect(screen.getByText("160")).toBeDefined();
    expect(screen.getByText("66")).toBeDefined();
    expect(screen.getByText(/12 Jan 2023 – 16 Des 2025/)).toBeDefined();
  });

  it("menampilkan peringatan aktif wilayah beserta ketertelusurannya", () => {
    render(<DistrictDetail district={kebayoran} detail={areaDetail} horizon="6H" />);

    expect(screen.getByText("91")).toBeDefined();
    expect(screen.getByText(/WRN-0069 · dari PRD-00148 · ambang dummy-v1/)).toBeDefined();
    expect(screen.getByText(/hanya peringatan berstatus active/i)).toBeDefined();
  });

  it("menampilkan WHY lengkap dengan asal faktor RULE/MODEL", () => {
    // CLAUDE.md §27: asal penjelasan tidak boleh disembunyikan.
    render(<DistrictDetail district={kebayoran} detail={areaDetail} horizon="6H" />);

    expect(screen.getByText("RULE")).toBeDefined();
    expect(screen.getByText("MODEL")).toBeDefined();
    expect(screen.getByText("Kepadatan kejadian historis")).toBeDefined();
    expect(screen.getByText("38%")).toBeDefined();
    expect(screen.getByText(/kontribusi aturan berbobot/i)).toBeDefined();
  });

  it("menampilkan skor prediksi tanpa kelas risiko", () => {
    render(<DistrictDetail district={kebayoran} detail={areaDetail} horizon="6H" />);

    expect(screen.getAllByText("54").length).toBeGreaterThan(0);
    expect(screen.getAllByText("tanpa kelas").length).toBeGreaterThan(0);
    expect(screen.getByText(/PRD-00116 · 30 Des 2025 · dummy-v1/)).toBeDefined();
  });

  it("menyatakan wilayah tanpa prediksi pada horizon peta", () => {
    render(<DistrictDetail district={districtOf("Tebet")} detail={areaDetail} horizon="6H" />);

    expect(
      screen.getByText(/tidak ada prediksi terpublikasi untuk wilayah ini pada horizon/i),
    ).toBeDefined();
  });

  it("menyatakan rincian yang tidak dapat diakses, bukan layar kosong", () => {
    // Backend menjawab 404 untuk wilayah di luar cakupan; antarmuka tidak menebak alasannya.
    render(<DistrictDetail district={districtOf("Cilandak")} detail={null} horizon="6H" />);

    expect(screen.getByText("Cilandak")).toBeDefined();
    expect(screen.getByText(/tidak ada rincian wilayah ini yang dapat ditampilkan/i)).toBeDefined();
  });

  it("meminta pengguna memilih wilayah bila belum ada yang dipilih", () => {
    render(<DistrictDetail district={null} detail={null} horizon="6H" />);

    expect(screen.getByText(/pilih salah satu kecamatan/i)).toBeDefined();
  });
});

describe("proyeksi titik ke bidang peta", () => {
  /**
   * Titik acuan diambil dari `locations` yang menjadi simpul terluar saat bentuk wilayah
   * dihitung. Nilai harapnya bukan angka yang dikarang untuk mencocokkan kode: ia keluar
   * dari menjalankan ulang pipeline pada `lib/geo.ts` dan terbukti menghasilkan kesepuluh
   * simpul `KECAMATAN_SHAPES` sampai satu angka di belakang koma.
   *
   * Test ini yang menahan tetapan proyeksi agar tidak diubah tanpa sadar — pergeseran
   * kecil di sini tidak menimbulkan galat apa pun, hanya titik yang "agak meleset".
   */
  const REFERENSI = [
    { code: "LOC-023", latitude: -6.209, longitude: 106.85, x: 875.2, y: 97.9 },
    { code: "LOC-033", latitude: -6.345, longitude: 106.824, x: 623.3, y: 1423.1 },
    { code: "LOC-006", latitude: -6.276, longitude: 106.767, x: 71.2, y: 750.8 },
    { code: "LOC-019", latitude: -6.257, longitude: 106.856, x: 933.3, y: 565.6 },
  ] as const;

  it("menempatkan titik acuan tepat di koordinat yang menghasilkan bentuk wilayah", () => {
    for (const titik of REFERENSI) {
      const [x, y] = projectLatLon(titik.latitude, titik.longitude);
      expect(x).toBeCloseTo(titik.x, 1);
      expect(y).toBeCloseTo(titik.y, 1);
    }
  });

  it("menaruh utara di atas", () => {
    const utara = projectLatLon(-6.209, 106.85);
    const selatan = projectLatLon(-6.345, 106.824);

    expect(utara[1]).toBeLessThan(selatan[1]);
  });

  it("mengenali titik di luar bidang gambar alih-alih menjepitkannya ke tepi", () => {
    expect(isWithinMap(projectLatLon(-6.24, 106.8))).toBe(true);
    expect(isWithinMap(projectLatLon(-5.0, 110.0))).toBe(false);
  });
});

describe("layer historis", () => {
  const historicalProps = {
    data,
    selected: "Kebayoran Baru",
    detail: areaDetail,
    layer: "historical" as const,
    months: 12 as const,
  };

  it("memberi label wilayah berisi cacah kejadian, bukan skor", () => {
    render(<RiskMap {...historicalProps} />);

    expect(
      screen.getByRole("link", {
        name: "Kebayoran Baru — 180 kejadian pada jendela yang ditampilkan",
      }),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: /skor risiko/ })).toBeNull();
  });

  it("menyatakan wilayah tanpa kejadian sebagai tidak tercatat, bukan nol", () => {
    render(<RiskMap {...historicalProps} />);

    expect(
      screen.getByRole("link", { name: "Cilandak — tidak ada kejadian tercatat" }),
    ).toBeDefined();
  });

  it("menggambar titik lokasi dan membuang yang jatuh di luar bidang gambar", () => {
    const { container } = render(<RiskMap {...historicalProps} />);

    // Dua dari tiga titik contoh berada di Jakarta Selatan; yang ketiga sengaja di luar.
    expect(container.querySelectorAll("circle")).toHaveLength(2);
  });

  it("tidak menggambar titik pada layer selain historis", () => {
    const { container } = render(<RiskMap {...historicalProps} layer="current" />);

    expect(container.querySelectorAll("circle")).toHaveLength(0);
  });

  it("menyatakan skalanya relatif terhadap jendela yang sedang tampil", () => {
    render(<RiskMap {...historicalProps} />);

    expect(screen.getByText(/Skala relatif · 260 kejadian pada jendela ini/)).toBeDefined();
    expect(screen.getByText(/bukan kelas risiko/)).toBeDefined();
  });

  it("meneruskan keterangan asal angka dari API apa adanya", () => {
    render(<RiskMap {...historicalProps} />);

    expect(screen.getByText(HISTORICAL_BASIS)).toBeDefined();
  });

  it("menampilkan jendela yang diminta beserta rentang data yang benar-benar ditemukan", () => {
    render(<RiskMap {...historicalProps} />);

    expect(screen.getByText("2024-12-28 s.d. 2025-12-27")).toBeDefined();
    expect(screen.getByText(/Data ditemukan 2025-01-03 s.d. 2025-12-24/)).toBeDefined();
  });

  it("hanya menawarkan pemilih jendela pada layer historis", () => {
    const { rerender } = render(<RiskMap {...historicalProps} />);
    expect(screen.getByRole("navigation", { name: "Jendela waktu historis" })).toBeDefined();

    rerender(<RiskMap {...historicalProps} layer="current" />);
    expect(screen.queryByRole("navigation", { name: "Jendela waktu historis" })).toBeNull();
  });

  it("membawa jendela terpilih di dalam tautan, dan menghilangkannya saat jendela bawaan", () => {
    render(<RiskMap {...historicalProps} months={36} />);

    const jendela = screen.getByRole("navigation", { name: "Jendela waktu historis" });
    expect(within(jendela).getByRole("link", { name: "Seluruh data" }).getAttribute("href")).toBe(
      "/peta?wilayah=Kebayoran+Baru&layer=historical&bulan=36",
    );
    expect(within(jendela).getByRole("link", { name: "12 bulan" }).getAttribute("href")).toBe(
      "/peta?wilayah=Kebayoran+Baru&layer=historical",
    );
  });
});

describe("skala warna historis", () => {
  it("tidak membagi dengan nol ketika belum ada kejadian sama sekali", () => {
    expect(historicalOpacity(0, 0)).toBeGreaterThan(0);
    expect(Number.isFinite(historicalOpacity(5, 0))).toBe(true);
  });

  it("memberi wilayah terbanyak kepekatan tertinggi", () => {
    expect(historicalOpacity(180, 180)).toBeGreaterThan(historicalOpacity(80, 180));
  });
});

describe("jendela historis dari alamat", () => {
  it("membuang panjang jendela yang tidak dilayani API", () => {
    expect(toHistoricalMonths("7")).toBe(12);
    expect(toHistoricalMonths("bukan angka")).toBe(12);
    expect(toHistoricalMonths(null)).toBe(12);
  });

  it("menerima panjang jendela yang dilayani", () => {
    expect(toHistoricalMonths("1")).toBe(1);
    expect(toHistoricalMonths("36")).toBe(36);
  });
});
