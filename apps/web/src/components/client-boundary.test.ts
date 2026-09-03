import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(process.cwd(), "src");

/**
 * Penjaga batas server/klien.
 *
 * ## Kegagalan yang dijaga
 *
 * Komponen bertanda `"use client"` berjalan di peramban, dan React **tidak dapat
 * mengirimkan fungsi** dari komponen server ke sana — props harus dapat diserialkan.
 * Melanggarnya menghasilkan:
 *
 * ```text
 * Error: Functions cannot be passed directly to Client Components
 * ```
 *
 * yang muncul **saat permintaan dilayani**, bukan saat build dan bukan saat test. Test
 * komponen merender komponen klien secara langsung, jadi batasnya tidak pernah dilewati
 * dan pelanggarannya tidak terlihat. Persis itu yang terjadi pada 3 September 2026:
 * `MapCanvas` diberi prop `hrefFor` berupa fungsi, `tsc` bersih, 394 test hijau, `next
 * build` sukses — dan beranda menjawab 500 di produksi.
 *
 * ## Cara memeriksanya
 *
 * Untuk setiap berkas `"use client"`, hanya komponen yang **diekspor** yang diperiksa —
 * dan hanya itu yang perlu. Komponen internal di dalam berkas yang sama tidak dapat
 * diimpor siapa pun, sehingga batas server/klien tidak pernah dilewati saat memanggilnya;
 * `FilterRow` pada `/prediksi` adalah contohnya, dan memaksanya memakai kata kunci hanya
 * akan memperumit kode tanpa mencegah apa pun.
 *
 * Bila kelak sebuah komponen klien yang diekspor memang hanya dipanggil komponen klien
 * lain dan perlu menerima callback, tambahkan ke `CALLBACK_ALLOWED` beserta alasannya —
 * bukan longgarkan aturannya.
 */

/** Komponen klien yang memang hanya dipanggil komponen klien lain. */
const CALLBACK_ALLOWED: Record<string, string> = {};

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return walk(path);
    return path.endsWith(".tsx") && !path.endsWith(".test.tsx") ? [path] : [];
  });
}

/**
 * Blok tipe props tiap komponen yang **diekspor**.
 *
 * Penelusuran dimulai dari `export function Nama(` lalu mengambil bagian di antara
 * `}: {` dan `}) {` yang paling dekat sesudahnya. Komponen internal sengaja dilewati:
 * ia tidak dapat diimpor komponen server mana pun.
 */
function exportedPropBlocks(source: string): string[] {
  const blocks: string[] = [];
  const exports = /export function \w+\(/g;
  let match = exports.exec(source);
  while (match !== null) {
    const tail = source.slice(match.index);
    const props = /\}:\s*\{([\s\S]*?)\}\)\s*\{/.exec(tail);
    if (props) blocks.push(props[1]);
    match = exports.exec(source);
  }
  return blocks;
}

describe("batas komponen server dan klien", () => {
  const clientFiles = walk(SRC).filter((path) => {
    const head = readFileSync(path, "utf8").slice(0, 200);
    return head.includes('"use client"');
  });

  it("menemukan komponen klien untuk diperiksa", () => {
    // Tanpa penegasan ini, kesalahan pada penelusuran berkas menghasilkan daftar kosong
    // dan seluruh pemeriksaan di bawah lulus tanpa memeriksa apa pun.
    expect(clientFiles.length).toBeGreaterThan(2);
  });

  it("tidak menerima prop bertipe fungsi pada komponen klien", () => {
    const offenders: string[] = [];

    for (const path of clientFiles) {
      const name = path.slice(SRC.length + 1);
      if (name in CALLBACK_ALLOWED) continue;

      for (const block of exportedPropBlocks(readFileSync(path, "utf8"))) {
        // Prop bertipe fungsi ditulis sebagai `nama?: (arg) => hasil`.
        const found = block.match(/^\s*\w+\??:\s*\([^)]*\)\s*=>/gm);
        if (found) offenders.push(`${name}: ${found.map((row) => row.trim()).join(", ")}`);
      }
    }

    expect(
      offenders,
      "prop bertipe fungsi tidak dapat dikirim dari komponen server — pakai kata kunci yang dapat diserialkan",
    ).toEqual([]);
  });
});
