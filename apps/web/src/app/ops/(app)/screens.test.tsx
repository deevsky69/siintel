import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { NAV_ITEMS } from "@/components/shell/navigation";

const APP_DIR = join(process.cwd(), "src/app/ops/(app)");

/**
 * Penjaga struktural antara menu dan rutenya.
 *
 * Dua kegagalan yang dijaga di sini tidak menimbulkan galat apa pun saat build:
 *
 * 1. **Submenu menunjuk rute yang tidak ada** — pengguna menekannya dan mendapat 404 pada
 *    aplikasi yang selebihnya bekerja. Ini paling mudah terjadi saat menu ditata ulang.
 * 2. **Layar tanpa keadaan memuat atau gagal** — CLAUDE.md §23 menuntut keduanya, dan
 *    ketiadaannya hanya terlihat ketika jaringan sedang lambat atau API sedang bermasalah,
 *    yaitu justru saat pengguna paling butuh diberi tahu apa yang terjadi.
 */
describe("menu dan rutenya", () => {
  const routes = NAV_ITEMS.map((item) => item.href).filter((href) => href !== "/ops");

  it("memiliki halaman untuk setiap submenu", () => {
    for (const href of routes) {
      const dir = join(APP_DIR, href.replace(/^\/ops\/?/, ""));
      expect(existsSync(join(dir, "page.tsx")), `${href} tidak punya page.tsx`).toBe(true);
    }
  });

  it("memiliki keadaan memuat dan gagal untuk setiap layar submenu", () => {
    for (const href of routes) {
      const dir = join(APP_DIR, href.replace(/^\/ops\/?/, ""));
      expect(existsSync(join(dir, "loading.tsx")), `${href} tanpa loading.tsx`).toBe(true);
      expect(existsSync(join(dir, "error.tsx")), `${href} tanpa error.tsx`).toBe(true);
    }
  });

  it("tidak meninggalkan layar yatim di luar menu", () => {
    // Layar yang tidak dapat dicapai dari menu mana pun akan terlupakan: ia tidak pernah
    // dibuka, tidak pernah diperbarui, dan lama-lama menampilkan sesuatu yang keliru tanpa
    // ada yang menyadarinya.
    const inMenu = new Set(
      NAV_ITEMS.map((item) => item.href.replace(/^\/ops\/?/, "")).filter(Boolean),
    );
    const onDisk = readdirSync(APP_DIR, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("("))
      .map((entry) => entry.name);

    // Tanpa penegasan ini, direktori yang gagal terbaca menghasilkan daftar kosong dan
    // perbandingan di bawah lulus tanpa memeriksa apa pun.
    expect(
      onDisk.length,
      "tidak ada layar terbaca — pemeriksaan ini tidak menguji apa pun",
    ).toBeGreaterThan(10);

    // 6 November 2026 (Mekanisme dan Fungsi SIGAP): layar harian SENGAJA keluar dari menu
    // tetapi rutenya dipertahankan untuk tautan lama dan data yang sudah tercatat. Daftar
    // ini tertutup: layar baru di luar menu tetap tertangkap di sini.
    const keptOffMenu = [
      "brief",
      "evaluasi",
      "informasi",
      // 12 November 2026 (catatan 179): tab di Laporan Petugas, bukan submenu.
      "input",
      "operasi",
      // 12 November 2026: dibaca lewat tab di Produk Bulanan / Analitik / Laporan Petugas,
      // atau hanya lewat alamat (pengaturan, wilayah rawan).
      "pembakuan",
      "pengaturan",
      "peringatan",
      "peringkat",
      "pola",
      "prediksi",
      "rekomendasi",
      // 10 November 2026: persetujuannya dilebur ke Produk Bulanan; layar tetap sebagai bacaan.
      "rencana-patroli",
      "skoring",
      "wilayah",
    ];
    expect(onDisk.filter((name) => !inMenu.has(name)).sort()).toEqual(keptOffMenu);
  });
});
