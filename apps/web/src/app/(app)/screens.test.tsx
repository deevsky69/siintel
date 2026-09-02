import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { NAV_ITEMS } from "@/components/shell/navigation";

const APP_DIR = join(process.cwd(), "src/app/(app)");

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
  const routes = NAV_ITEMS.map((item) => item.href).filter((href) => href !== "/");

  it("memiliki halaman untuk setiap submenu", () => {
    for (const href of routes) {
      const dir = join(APP_DIR, href.slice(1));
      expect(existsSync(join(dir, "page.tsx")), `${href} tidak punya page.tsx`).toBe(true);
    }
  });

  it("memiliki keadaan memuat dan gagal untuk setiap layar submenu", () => {
    for (const href of routes) {
      const dir = join(APP_DIR, href.slice(1));
      expect(existsSync(join(dir, "loading.tsx")), `${href} tanpa loading.tsx`).toBe(true);
      expect(existsSync(join(dir, "error.tsx")), `${href} tanpa error.tsx`).toBe(true);
    }
  });

  it("tidak meninggalkan layar yatim di luar menu", () => {
    // Layar yang tidak dapat dicapai dari menu mana pun akan terlupakan: ia tidak pernah
    // dibuka, tidak pernah diperbarui, dan lama-lama menampilkan sesuatu yang keliru tanpa
    // ada yang menyadarinya.
    const inMenu = new Set(NAV_ITEMS.map((item) => item.href.slice(1)).filter(Boolean));
    const onDisk = readdirSync(APP_DIR, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("("))
      .map((entry) => entry.name);

    // Tanpa penegasan ini, direktori yang gagal terbaca menghasilkan daftar kosong dan
    // perbandingan di bawah lulus tanpa memeriksa apa pun.
    expect(
      onDisk.length,
      "tidak ada layar terbaca — pemeriksaan ini tidak menguji apa pun",
    ).toBeGreaterThan(10);

    expect(onDisk.filter((name) => !inMenu.has(name))).toEqual([]);
  });
});
