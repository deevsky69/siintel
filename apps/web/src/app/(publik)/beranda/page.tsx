import Link from "next/link";
import { Suspense } from "react";
import { ImbauanBerlaku } from "./imbauan-berlaku";

export const metadata = { title: "PREDIKSI PRESISI" };

/**
 * Halaman muka untuk pengunjung yang belum masuk.
 *
 * Ditampilkan pada alamat `/` lewat *rewrite* di middleware, bukan redirect: alamatnya
 * tetap `/` sehingga pengunjung tidak perlu tahu ada dua halaman berbeda di baliknya, dan
 * pengguna yang sudah masuk tetap mendapat dashboard pada alamat yang sama.
 *
 * Isinya sengaja hanya dua pilihan. Halaman muka lembaga biasanya tergoda memuat berita,
 * statistik, dan tautan lain-lain; di sini keduanya justru berbahaya — angka kamtibmas di
 * halaman publik adalah data intelijen, dan tidak satu pun boleh keluar tanpa keputusan
 * publikasi (CLAUDE.md §24). Karena itu halaman ini **tidak memuat satu pun angka**.
 *
 * Sejak 9 September 2026 ada satu tambahan, dan ia justru menegaskan aturan yang sama:
 * imbauan yang SUDAH melewati keputusan publikasi. Ia tampil bukan karena kanal publik
 * dilonggarkan, melainkan karena kini ada pejabat yang berwenang memutuskan apa yang boleh
 * keluar — `public_alert:publish` pada Pimpinan. Peringatan dini yang belum diumumkan tetap
 * tidak pernah sampai ke halaman ini, dan tidak ada satu angka pun yang ikut: tanpa skor,
 * tanpa cacah kejadian, tanpa peringkat wilayah.
 */
export default function BerandaPublik() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden p-6">
      <AnimatedBackdrop />

      <div className="relative z-10 w-full max-w-lg text-center">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-xl border border-accent/30 bg-accent/10 font-heading text-xl font-bold text-accent shadow-glow">
          PP
        </div>

        <h1 className="font-heading text-3xl font-bold tracking-wide text-ink sm:text-4xl">
          PREDIKSI PRESISI
        </h1>
        <p className="mt-2 text-xs uppercase tracking-[0.2em] text-accent-soft">
          Polres Metro Jakarta Selatan
        </p>
        <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-ink-muted">
          Deteksi dini kerawanan kamtibmas. Laporan warga menjadi salah satu masukannya.
        </p>

        <div className="mt-9 flex flex-col items-stretch justify-center gap-3 sm:flex-row">
          <Link
            href="/lapor"
            className="rounded-lg border border-accent/50 bg-accent/10 px-6 py-3 font-heading text-sm font-semibold uppercase tracking-wider text-accent transition-colors hover:bg-accent/20"
          >
            Lapor Kejadian
          </Link>
          <Link
            href="/masuk"
            className="rounded-lg border border-base-700 px-6 py-3 font-heading text-sm font-semibold uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
          >
            Masuk Petugas
          </Link>
        </div>

        {/* Dibungkus Suspense supaya dua tombol di atas terlihat SEKETIKA. Halaman ini
            paling sering dibuka dari ponsel dengan jaringan buruk, dan menahan seluruh
            halaman demi bagian tambahan membuat pengunjung yang datang untuk melapor
            justru menunggu. */}
        <Suspense fallback={null}>
          <ImbauanBerlaku />
        </Suspense>

        <p className="mt-8 text-xs leading-relaxed text-ink-faint">
          Untuk keadaan darurat yang sedang berlangsung, hubungi <strong>110</strong>. Laporan
          melalui halaman ini dibaca petugas pada jam kerja dan <strong>bukan pengganti</strong>{" "}
          laporan polisi resmi.
        </p>
      </div>
    </main>
  );
}

/**
 * Latar beranimasi.
 *
 * Murni CSS — tanpa canvas, tanpa pustaka, tanpa JavaScript. Halaman muka publik adalah
 * halaman yang paling mungkin dibuka dari ponsel dengan jaringan buruk, dan animasi yang
 * menuntut unduhan tambahan membuatnya justru terasa lebih lambat.
 *
 * `motion-reduce:animate-none` menghormati setelan sistem pengunjung yang meminta gerakan
 * dikurangi; gerak latar yang tidak dapat dihentikan adalah masalah aksesibilitas nyata,
 * bukan sekadar selera.
 */
function AnimatedBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      {/* Kisi tipis — mengutip bidang peta tanpa menampilkan peta sungguhan. */}
      <div
        className="absolute inset-0 opacity-[0.09]"
        style={{
          backgroundImage:
            "linear-gradient(rgb(var(--accent)) 1px, transparent 1px), linear-gradient(90deg, rgb(var(--accent)) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
        }}
      />

      {/* Dua pendar yang bergerak lambat. Lambat dengan sengaja: latar yang bergerak cepat
          menarik mata menjauh dari dua tombol yang menjadi satu-satunya isi halaman. */}
      <div className="absolute -left-24 top-[-10%] h-[26rem] w-[26rem] animate-pulse rounded-full bg-accent/10 blur-3xl motion-reduce:animate-none [animation-duration:7s]" />
      <div className="absolute -right-20 bottom-[-12%] h-[22rem] w-[22rem] animate-pulse rounded-full bg-risk-critical/10 blur-3xl motion-reduce:animate-none [animation-duration:9s]" />

      {/* Peredup di tepi supaya teks di tengah tetap punya kontras yang cukup. */}
      <div className="absolute inset-0 bg-gradient-to-b from-base-950/70 via-transparent to-base-950" />
    </div>
  );
}
