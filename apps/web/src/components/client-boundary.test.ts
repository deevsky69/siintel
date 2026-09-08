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
 * `FilterRow` pada `/prediksi` adalah contohnya.
 *
 * ## Server action adalah pengecualian yang sah, dan dikenali dari tipenya
 *
 * Fungsi bertanda `"use server"` **boleh** dikirim ke komponen klien: yang menyeberang
 * bukan fungsinya melainkan rujukan yang dapat diserialkan, dan React memanggilnya kembali
 * di server. `StatusForm` menerimanya sebagai prop `action`, dan itu benar.
 *
 * Pembedanya diambil dari **tipe kembaliannya**: server action wajib `async`, sehingga
 * tipenya selalu berujung `Promise<...>`. Callback biasa seperti `hrefFor: (s) => string`
 * tidak — dan justru itulah yang menjatuhkan beranda ke 500.
 *
 * Heuristik ini tidak sempurna: callback klien yang kebetulan `async` akan lolos. Tetapi
 * yang dijaga adalah **kelas kegagalan yang sudah benar-benar terjadi**, dan penjaga yang
 * menolak pemakaian yang sah akan dilonggarkan orang berikutnya sampai tidak menjaga
 * apa-apa lagi.
 *
 * Bila kelak sebuah komponen klien yang diekspor memang perlu menerima callback sinkron
 * dari komponen klien lain, tambahkan ke `CALLBACK_ALLOWED` beserta alasannya — bukan
 * longgarkan aturannya.
 */

/**
 * Komponen klien yang memang hanya dipanggil komponen klien lain.
 *
 * Masuk daftar ini **tidak** membuat pemeriksaannya hilang. Ia diganti pemeriksaan yang
 * lebih tepat: seluruh berkas yang mengimpornya wajib ikut bertanda `"use client"`. Daftar
 * putih yang hanya berisi janji akan menjadi tempat menyembunyikan pelanggaran; yang ini
 * gagal begitu sebuah komponen server mengimpornya.
 */
const CALLBACK_ALLOWED: Record<string, string> = {
  "components/shell/topbar.tsx":
    "prop `onMenu` datang dari ShellFrame, yang juga komponen klien — laci navigasi " +
    "memerlukan keadaan, dan keadaan tidak dapat hidup di komponen server.",
};

/** Jalur modul yang diimpor sebuah berkas, dinyatakan relatif terhadap `src`. */
function importedModules(path: string, source: string): string[] {
  const specifiers = [...source.matchAll(/from\s+"([^"]+)"/g)].map((match) => match[1]);
  const here = path
    .slice(SRC.length + 1)
    .split("/")
    .slice(0, -1);

  return specifiers.flatMap((specifier) => {
    if (specifier.startsWith("@/")) return [specifier.slice(2)];
    if (!specifier.startsWith(".")) return [];
    const parts = [...here];
    for (const segment of specifier.split("/")) {
      if (segment === ".") continue;
      else if (segment === "..") parts.pop();
      else parts.push(segment);
    }
    return [parts.join("/")];
  });
}

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

  it("hanya komponen klien yang mengimpor komponen ber-callback", () => {
    const violations: string[] = [];

    for (const allowed of Object.keys(CALLBACK_ALLOWED)) {
      const target = allowed.replace(/\.tsx$/, "");
      const importers = walk(SRC).filter((path) =>
        importedModules(path, readFileSync(path, "utf8")).includes(target),
      );

      // Tidak ada yang mengimpornya berarti daftar putihnya sudah basi — dan daftar putih
      // basi adalah pengecualian yang tidak lagi diawasi siapa pun.
      expect(
        importers,
        `tidak ada yang mengimpor ${allowed}; hapus dari CALLBACK_ALLOWED`,
      ).not.toHaveLength(0);

      for (const importer of importers) {
        const head = readFileSync(importer, "utf8").slice(0, 200);
        if (!head.includes('"use client"')) {
          violations.push(`${importer.slice(SRC.length + 1)} mengimpor ${allowed}`);
        }
      }
    }

    expect(
      violations,
      "komponen server mengimpor komponen klien yang menerima callback sinkron",
    ).toEqual([]);
  });

  it("tidak menerima prop bertipe fungsi pada komponen klien", () => {
    const offenders: string[] = [];

    for (const path of clientFiles) {
      const name = path.slice(SRC.length + 1);
      if (name in CALLBACK_ALLOWED) continue;

      for (const block of exportedPropBlocks(readFileSync(path, "utf8"))) {
        // Prop bertipe fungsi ditulis sebagai `nama?: (arg) => hasil`. Yang berujung
        // `Promise<...>` dilewati: itu bentuk server action, yang sah menyeberang.
        const found = (block.match(/^\s*\w+\??:\s*\([^)]*\)\s*=>[^;]*/gm) ?? []).filter(
          (row) => !/=>\s*Promise</.test(row),
        );
        if (found.length > 0) {
          offenders.push(`${name}: ${found.map((row) => row.trim()).join(", ")}`);
        }
      }
    }

    expect(
      offenders,
      "prop bertipe fungsi tidak dapat dikirim dari komponen server — pakai kata kunci yang dapat diserialkan",
    ).toEqual([]);
  });
});
