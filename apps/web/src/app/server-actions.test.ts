import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Aturan Next: berkas `"use server"` **hanya boleh mengekspor fungsi async**.
 *
 * Melanggarnya tidak menggagalkan `next build`, tidak menggagalkan typecheck, dan tidak
 * menggagalkan satu pun test komponen — Next baru menolak modulnya **ketika action
 * dipanggil**. Akibatnya sebuah formulir dapat tampil sempurna di layar, lolos seluruh
 * pemeriksaan, lalu menjawab 500 pertama kali ditekan.
 *
 * Itu persis yang terjadi pada `rekomendasi/actions.ts`, yang sempat mengekspor
 * `const IDLE`. Test ini menjaga seluruh server action yang ada maupun yang akan datang.
 */

const APP = join(import.meta.dirname);

function serverActionFiles(dir: string): string[] {
  const found: string[] = [];

  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      found.push(...serverActionFiles(path));
      continue;
    }
    if (!/\.tsx?$/.test(entry)) continue;

    const source = readFileSync(path, "utf8");
    if (/^\s*["']use server["']\s*;/m.test(source)) found.push(path);
  }

  return found;
}

/**
 * Setiap `export` yang akan benar-benar ada di JavaScript hasil kompilasi dan bukan
 * fungsi async.
 *
 * `export type` dan `export interface` dikecualikan karena keduanya **dihapus** oleh
 * TypeScript: modul yang dihasilkan tidak memuatnya, sehingga Next tidak pernah
 * melihatnya. Ini bukan kelonggaran yang dikarang — `peringatan/actions.ts` mengekspor
 * sebuah tipe dan alur acknowledge-nya terbukti berjalan sungguhan terhadap backend.
 *
 * Yang berbahaya adalah nilai: `export const`, `let`, `var`, `class`, dan fungsi
 * non-async. Itulah yang membuat Next menolak seluruh modul saat action dipanggil.
 */
function offendingExports(source: string): string[] {
  return source
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /^export\b/.test(line))
    .filter((line) => !/^export\s+(type|interface)\b/.test(line))
    .filter((line) => !/^export\s+async\s+function\b/.test(line));
}

describe("berkas server action", () => {
  const files = serverActionFiles(APP);

  it("ada dan ditemukan oleh pemindai ini", () => {
    // Bila pemindainya sendiri rusak, seluruh test di bawah lulus tanpa memeriksa apa pun.
    expect(files.length).toBeGreaterThan(0);
  });

  it.each(files.map((file) => [file.slice(APP.length + 1), file]))(
    "%s hanya mengekspor fungsi async",
    (_label, file) => {
      const offenders = offendingExports(readFileSync(file, "utf8"));

      expect(offenders).toEqual([]);
    },
  );

  it("mengenali pelanggaran, bukan sekadar meluluskan semuanya", () => {
    // Tanpa ini, test di atas akan tetap hijau seandainya `offendingExports` selalu kosong.
    expect(offendingExports("export const IDLE = { error: null };")).toHaveLength(1);
    expect(offendingExports("export function decide() {}")).toHaveLength(1);
    expect(offendingExports("export class Guard {}")).toHaveLength(1);
    // Dihapus saat kompilasi, jadi tidak pernah sampai ke Next.
    expect(offendingExports("export type State = { error: string };")).toHaveLength(0);
    expect(offendingExports("export async function decide() {}")).toHaveLength(0);
  });
});
