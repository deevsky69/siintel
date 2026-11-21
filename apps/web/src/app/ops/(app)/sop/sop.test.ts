import { describe, expect, it } from "vitest";
import { MODUL, MUATAN, PENGGUNA_PRODUK, RINGKASAN_SOP, SUMBER_DATA, VALIDASI } from "./content";

/**
 * Halaman SOP adalah kutipan naskah Taskap revisi. Test ini mengunci butir yang paling mudah
 * bergeser tanpa disadari: urutan validasi berjenjang (Gambar 4.3) dan baris Tabel 4.17.
 */
describe("muatan dan desain SOP mengikuti naskah Taskap revisi", () => {
  it("validasi berjenjang: analis, KBO, Wakasat, Kasat, Kapolres", () => {
    expect([...VALIDASI]).toEqual([
      "Analis tim inti",
      "KBO Satintelkam",
      "Wakasatintelkam",
      "Kasatintelkam",
      "Kapolres (keputusan)",
    ]);
  });

  it("lima modul berurutan, masing-masing dengan bagian SOP dan layar yang menjalankannya", () => {
    expect(MODUL.map((m) => `${m.no} ${m.nama} — ${m.sop}`)).toEqual([
      "Modul 1 Pembakuan Data — SOP Pengelolaan Data",
      "Modul 2 Peta dan Indeks Kerawanan Wilayah — SOP Penilaian Kerawanan",
      "Modul 3 Prediksi Kelurahan Prioritas (AI) — SOP Prediksi",
      "Modul 4 Draf Rekomendasi dan Validasi — SOP Validasi dan Penyampaian",
      "Modul 5 Evaluasi Ketepatan — SOP Evaluasi",
    ]);
    for (const modul of MODUL) expect(modul.layar.length).toBeGreaterThan(0);
  });

  it("Tabel 4.17: enam bagian SOP dengan kelemahan yang dijawab", () => {
    expect(MUATAN.map((b) => [b.bagian, b.modul, b.kelemahan])).toEqual([
      ["Pengelolaan data", "Modul 1 Pembakuan data", "W3"],
      ["Penilaian kerawanan", "Modul 2 Peta dan IKW", "W5"],
      ["Prediksi", "Modul 3 Prediksi AI", "W4"],
      ["Validasi dan penyampaian", "Modul 4 Rekomendasi", "W4"],
      ["Evaluasi", "Modul 5 Evaluasi", "W5"],
      ["Keamanan informasi", "Dasbor dan hak akses", "W3"],
    ]);
    expect(MUATAN[4].isi).toBe(
      "Cakupan kejadian, mutu draf, waktu kerja, dan catatan tindak lanjut",
    );
  });

  it("sumber data, pengguna produk, dan sembilan ketentuan SOP", () => {
    expect(SUMBER_DATA).toHaveLength(4);
    expect([...PENGGUNA_PRODUK]).toEqual(["Bagops", "Satsamapta", "Satbinmas", "Polsek"]);
    expect(RINGKASAN_SOP).toHaveLength(9);
    expect(RINGKASAN_SOP[6][1]).toContain("analis, KBO, Wakasatintelkam, dan Kasatintelkam");
  });
});
