import Link from "next/link";
import { Suspense } from "react";
import { PolriEmblem } from "@/components/warga/brand";
import { LoginForm } from "./login-form";

export const metadata = { title: "Masuk Petugas — SIGAP" };

/**
 * Halaman masuk untuk personel (mockup `sigap-login-petugas`, 10 November 2026): bidang
 * navy dengan sapuan cahaya emas yang bergerak pelan, lambang berhalo, judul SIGAP, kartu
 * putih bergaris emas di atasnya, dan dua tautan bagi warga yang tersasar.
 *
 * Sejak kanal publik ada, halaman ini juga menjadi tempat warga tersasar: tombol "Masuk
 * petugas" bertetangga dengan "Lapor kejadian" di halaman muka, dan salah tekan itu wajar.
 * Karena itu ada jalan kembali yang terlihat **tanpa harus menekan tombol mundur peramban**,
 * dan tautannya menyebut "Lapor kejadian" secara eksplisit, bukan hanya "kembali".
 *
 * Dibungkus `.warga` supaya memakai token sisi masyarakat (selalu terang di kartunya) dan
 * tidak terpengaruh pengalih tema /ops; animasi latar mockup (shader WebGL) diganti sapuan
 * CSS ringan yang berhenti pada `prefers-reduced-motion`.
 */
export default function LoginPage() {
  return (
    <div className="warga masuk">
      <main className="masuk-hero">
        <div className="masuk-scan" aria-hidden="true" />
        <div className="relative z-[1] flex w-full flex-col items-center justify-center px-6 pb-11 pt-8 text-center">
          <div className="masuk-emblem">
            <PolriEmblem size={256} className="relative h-[84px] w-auto" />
          </div>
          <h1 className="mt-4 text-[clamp(30px,4.6vw,44px)] text-white">SIGAP</h1>
          <p className="mt-2 max-w-[70ch] text-base text-[rgb(var(--warga-soft))]">
            Sistem Inteligensi Geospasial dan Analitik Prediktif
          </p>
          <p className="mt-1 text-sm font-medium text-[rgb(var(--warga-goldl))]">
            Polres Metro Jakarta Selatan
          </p>

          <section className="masuk-card mt-6" aria-labelledby="masuk-judul">
            <h2 id="masuk-judul" className="text-[22px] text-[rgb(var(--warga-navy))]">
              Masuk
            </h2>
            <p className="mb-4 mt-1 text-sm text-ink-faint">Gunakan akun petugas Anda.</p>
            {/* useSearchParams membuat formulir dirender di klien; Suspense diperlukan
                agar halaman tetap dapat di-prerender. */}
            <Suspense fallback={<div className="h-[232px] animate-pulse bg-base-950" />}>
              <LoginForm />
            </Suspense>
            <p className="mt-4 border-t border-base-800 pt-4 text-center text-[13px] leading-relaxed text-ink-faint">
              Akses terbatas untuk personel berwenang. Seluruh percobaan masuk dicatat pada audit
              trail.
            </p>
          </section>

          <p className="mt-6 text-sm text-[rgb(var(--warga-soft))]">
            Bukan petugas dan ingin melaporkan kejadian?
          </p>
          <div className="masuk-alt mt-3 flex flex-wrap justify-center gap-2.5">
            <Link href="/lapor" className="is-gold">
              Lapor kejadian
            </Link>
            <Link href="/" className="is-white">
              Halaman muka
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
