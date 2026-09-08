/**
 * Tema terang dan gelap.
 *
 * ## Tiga keadaan, bukan dua
 *
 * ```text
 * "terang"  pengguna memilih terang
 * "gelap"   pengguna memilih gelap
 * "sistem"  ikut setelan perangkat, dan BERUBAH bila setelan itu berubah
 * ```
 *
 * Keadaan ketiga bukan hiasan. Ponsel yang beralih gelap otomatis saat malam adalah hal
 * yang sudah diharapkan pemakainya; aplikasi yang mengabaikannya terasa rusak. Karena itu
 * "sistem" adalah nilai bawaan, dan pilihan tersimpan hanya dibuat ketika pengguna benar-
 * benar menekan tombolnya.
 */

export type ThemeChoice = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "presisi-tema";

/**
 * Skrip yang memasang kelas `dark` sebelum halaman tergambar.
 *
 * Ditulis sebagai teks, bukan modul, karena ia harus berjalan **sinkron di dalam `<head>`**.
 * Apa pun yang menunggu React sudah terlambat: halaman sudah tergambar sekali dengan tema
 * yang salah, dan pengguna melihat kedipannya.
 *
 * Dibungkus `try` karena `localStorage` melempar galat pada peramban yang memblokir
 * penyimpanan situs. Kegagalan membaca pilihan bukan alasan menggagalkan seluruh halaman —
 * jatuhnya ke setelan sistem sudah merupakan jawaban yang benar.
 */
export const THEME_BOOTSTRAP = `(function(){try{
var c=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
var d=c==="dark"||(c!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);
document.documentElement.classList.toggle("dark",d);
}catch(e){document.documentElement.classList.add("dark");}})();`;

/** Menerjemahkan pilihan menjadi keadaan nyata, dengan setelan perangkat sebagai rujukan. */
export function resolveTheme(choice: ThemeChoice): "light" | "dark" {
  if (choice === "system") {
    return typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return choice;
}

/** Membaca pilihan tersimpan. Ketiadaan pilihan berarti "sistem", bukan "gelap". */
export function readThemeChoice(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

/** Menyimpan pilihan dan menerapkannya. `"system"` menghapus pilihan, bukan menyimpannya. */
export function applyThemeChoice(choice: ThemeChoice): void {
  try {
    if (choice === "system") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    // Penyimpanan diblokir: tema tetap berganti untuk kunjungan ini, hanya tidak diingat.
  }
  document.documentElement.classList.toggle("dark", resolveTheme(choice) === "dark");
}
