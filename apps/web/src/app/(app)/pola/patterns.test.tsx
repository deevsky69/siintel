import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PatternDistribution, PatternProfile, ThreatTypeCount } from "@/lib/patterns";
import { humanize, resolveThreatType, shareText } from "./dna";
import { PatternDna } from "./pattern-dna";

/**
 * Uji layar Crime Pattern DNA.
 *
 * Yang dijaga di sini bukan rupa layarnya melainkan janjinya: persentase tidak pernah
 * tampil tanpa penyebutnya, urutan dari backend tidak diubah, layar tidak menandai apa pun
 * sebagai "signifikan", dan tidak ada satu pun kalimat yang menjadikan sebaran masa lalu
 * terbaca sebagai prediksi (CLAUDE.md §11, §27).
 */

const available: ThreatTypeCount[] = [
  { threat_type: "CURANMOR", incidents: 464 },
  { threat_type: "CURAT", incidents: 282 },
  { threat_type: "TAWURAN", incidents: 129 },
];

function ranked(id: string, label: string, buckets: [string, number][]): PatternDistribution {
  return {
    id,
    label,
    ordering: "rank",
    denominator: 464,
    buckets: buckets.map(([key, incidents]) => ({
      key,
      label: key,
      incidents,
      share_percent: Math.round((1000 * incidents) / 464) / 10,
    })),
  };
}

const hours: PatternDistribution = {
  id: "hour",
  label: "Jam kejadian",
  ordering: "natural",
  denominator: 464,
  buckets: Array.from({ length: 24 }, (_, hour) => ({
    key: String(hour),
    label: `${String(hour).padStart(2, "0")}.00`,
    incidents: hour === 20 ? 47 : 0,
    share_percent: hour === 20 ? 10.1 : 0,
  })),
};

const profile: PatternProfile = {
  threat_type: "CURANMOR",
  incidents: 464,
  date_from: "2023-01-01",
  date_to: "2025-12-31",
  sample_note:
    "Seluruh persentase profil ini dihitung dari 464 kejadian CURANMOR dalam cakupan Anda; satu kejadian setara 0,2 persen poin.",
  where: [
    ranked("kecamatan", "Kecamatan", [
      ["Kebayoran Baru", 79],
      ["Tebet", 76],
    ]),
    ranked("location_type", "Kategori TKP", [
      ["Parkiran", 114],
      ["Permukiman", 102],
    ]),
  ],
  when: [hours],
  how: [
    ranked("modus", "Modus", [
      ["kelalaian_pengguna", 124],
      ["kunci_t", 113],
    ]),
  ],
  target: [
    ranked("target_type", "Sasaran", [
      ["motor", 232],
      ["mobil", 232],
    ]),
  ],
  repeat: {
    grids_with_incidents: 33,
    repeat_grids: 33,
    single_incident_grids: 0,
    incidents_in_repeat_grids: 464,
    share_percent: 100,
    denominator: 464,
    grids: [
      {
        grid_id: "JKS-001",
        kecamatan: "Kebayoran Baru",
        incidents: 25,
        share_percent: 5.4,
        first_date: "2023-01-07",
        last_date: "2025-12-25",
        span_days: 1083,
      },
    ],
    basis: "Sebuah grid dihitung berulang bila memuat sekurang-kurangnya 2 kejadian…",
  },
  time_basis: "Jam diambil dari kolom incident_time dan hari dari incident_date.",
};

const ANALYSIS_BASIS =
  "Profil ini adalah sebaran kejadian yang SUDAH TERJADI pada tabel crime_incidents — bukan prediksi.";

function screenDna(props: Partial<Parameters<typeof PatternDna>[0]> = {}) {
  return render(
    <PatternDna
      available={available}
      selected="CURANMOR"
      profile={profile}
      source={{ date_from: "2023-01-01", date_to: "2025-12-31", incidents: 1200 }}
      scopeBasis="Seluruh angka dihitung dari kejadian di seluruh wilayah Polres."
      analysisBasis={ANALYSIS_BASIS}
      {...props}
    />,
  );
}

/** Tanggal seperti yang dirakit layar, supaya uji tidak terikat pada satu versi ICU. */
const asDate = (iso: string) =>
  new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

/** Kueri dibatasi pada satu panel: label yang sama muncul di lebih dari satu dimensi. */
function panel(title: string | RegExp) {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
}

describe("pemilihan jenis gangguan", () => {
  it("memakai jenis yang diminta bila dikenal", () => {
    expect(resolveThreatType(available, "CURAT")).toBe("CURAT");
  });

  it("mencocokkan tanpa memandang huruf besar-kecil", () => {
    expect(resolveThreatType(available, "curanmor")).toBe("CURANMOR");
  });

  it("jatuh ke jenis terbanyak bila nama tidak dikenal", () => {
    // Tautan usang atau jenis di luar cakupan wilayah tidak boleh membuka layar kosong.
    expect(resolveThreatType(available, "TIDAK_ADA")).toBe("CURANMOR");
    expect(resolveThreatType(available, null)).toBe("CURANMOR");
  });

  it("tidak memilih apa pun bila tidak ada kejadian yang terlihat", () => {
    expect(resolveThreatType([], "CURANMOR")).toBeNull();
  });
});

describe("pemformatan nilai", () => {
  it("selalu menyebut penyebut di samping persentase", () => {
    expect(shareText(24.6, 464)).toBe("24,6% dari 464 kejadian");
  });

  it("merapikan nilai taksonomi bergaris bawah", () => {
    expect(humanize("kelalaian_pengguna")).toBe("Kelalaian pengguna");
  });

  it("membiarkan nama yang sudah tertulis rapi", () => {
    // Merapikan "Pusat Aktivitas" justru akan merusak kapitalisasinya.
    expect(humanize("Pusat Aktivitas")).toBe("Pusat Aktivitas");
    expect(humanize("Kebayoran Baru")).toBe("Kebayoran Baru");
  });
});

describe("layar Crime Pattern DNA", () => {
  it("menampilkan kelima dimensi berdampingan", () => {
    screenDna();

    for (const code of ["WHERE", "WHEN", "HOW", "TARGET", "REPEAT"]) {
      expect(screen.getByRole("heading", { name: new RegExp(`^${code} ·`) })).toBeDefined();
    }
  });

  it("menyatakan bahwa ini bukan prediksi sebelum angka apa pun", () => {
    screenDna();

    expect(screen.getByText(/bukan prediksi/)).toBeDefined();
    // Tidak ada skor risiko maupun tingkat keyakinan di layar analisis deskriptif.
    expect(screen.queryByText(/skor risiko/i)).toBeNull();
    expect(screen.queryByText(/keyakinan/i)).toBeNull();
  });

  it("tidak pernah menulis persentase tanpa penyebutnya", () => {
    screenDna();

    const where = panel(/^WHERE ·/);
    expect(where.getByText("17,0% dari 464 kejadian")).toBeDefined();
    expect(where.getByText("24,6% dari 464 kejadian")).toBeDefined();
  });

  it("menghormati urutan peringkat dari backend", () => {
    screenDna();

    const rows = panel(/^HOW ·/).getAllByRole("listitem");
    expect(rows[0].textContent).toContain("Kelalaian pengguna");
    expect(rows[1].textContent).toContain("Kunci t");
  });

  it("menampilkan seluruh 24 jam, termasuk jam tanpa kejadian", () => {
    screenDna();

    const when = panel(/^WHEN ·/);
    expect(when.getByText("47 · 10,1% dari 464 kejadian")).toBeDefined();
    // Dua puluh tiga jam sisanya tetap dikirim sebagai nol, bukan dihilangkan dari daftar.
    expect(when.getAllByText("0 · 0,0% dari 464 kejadian")).toHaveLength(23);
  });

  it("membawa rentang tanggal pada setiap grid berulang", () => {
    screenDna();

    const repeat = panel(/^REPEAT ·/);
    // Tanpa rentang, "25 kejadian di satu grid" tidak dapat dibaca maknanya.
    expect(repeat.getByText("JKS-001")).toBeDefined();
    expect(repeat.getByText(`${asDate("2023-01-07")} – ${asDate("2025-12-25")}`)).toBeDefined();
    expect(repeat.getByText("(1083 hari)")).toBeDefined();
  });

  it("menyatakan seberapa rapuh persentasenya", () => {
    screenDna();

    expect(screen.getByText(/satu kejadian setara 0,2 persen poin/)).toBeDefined();
  });

  it("menaruh jenis terpilih dan seluruh pilihan lain di alamat", () => {
    screenDna();

    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/pola?jenis=CURANMOR",
      "/pola?jenis=CURAT",
      "/pola?jenis=TAWURAN",
    ]);
    expect(screen.getByRole("link", { current: true }).textContent).toContain("Curanmor");
  });

  it("menyatakan keadaan kosong alih-alih menampilkan persentase dari nol kejadian", () => {
    screenDna({ profile: null, selected: null });

    expect(screen.getByText(/Belum ada kejadian yang dapat diprofilkan/)).toBeDefined();
    expect(screen.queryByRole("heading", { name: /^WHERE ·/ })).toBeNull();
  });

  it("menyatakan keadaan kosong bila kewenangan tidak memuat satu kejadian pun", () => {
    screenDna({ available: [], profile: null, selected: null });

    expect(
      screen.getByText(/Tidak ada kejadian yang dapat ditampilkan untuk kewenangan Anda/),
    ).toBeDefined();
  });
});
