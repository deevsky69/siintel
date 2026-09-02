import Link from "next/link";
import { Suspense } from "react";
import { LoginForm } from "./login-form";

export const metadata = { title: "Masuk — PREDIKSI PRESISI" };

/**
 * Halaman masuk untuk personel.
 *
 * Sejak kanal publik ada, halaman ini juga menjadi tempat warga tersasar: tombol "Masuk
 * Petugas" bertetangga dengan "Lapor Kejadian" di halaman muka, dan salah tekan itu
 * wajar. Karena itu ada jalan kembali yang terlihat **tanpa harus menekan tombol mundur
 * peramban** — pengunjung yang merasa tersesat cenderung menutup tab, bukan mencari cara
 * kembali.
 *
 * Tautannya menyebut "Lapor Kejadian" secara eksplisit, bukan hanya "kembali": yang
 * dibutuhkan warga yang salah tekan bukan halaman muka, melainkan tujuan yang tadi
 * dimaksudkannya.
 */

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-lg border border-accent/30 bg-accent/10 font-heading text-lg font-bold text-accent">
            PP
          </div>
          <h1 className="font-heading text-xl font-bold tracking-wide text-ink">
            PREDIKSI PRESISI
          </h1>
          <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-muted">
            Polres Metro Jakarta Selatan
          </p>
        </div>

        {/* useSearchParams membuat formulir dirender di klien; Suspense diperlukan
            agar halaman tetap dapat di-prerender. */}
        <Suspense fallback={<div className="panel h-[268px] animate-pulse" />}>
          <LoginForm />
        </Suspense>

        <p className="mt-6 text-center text-[11px] leading-relaxed text-ink-muted">
          Akses terbatas untuk personel berwenang. Seluruh percobaan masuk dicatat pada audit trail.
        </p>

        <div className="mt-6 border-t border-base-800 pt-5 text-center">
          <p className="text-[11px] leading-relaxed text-ink-muted">
            Bukan petugas dan ingin melaporkan kejadian?
          </p>
          <div className="mt-2.5 flex flex-col items-center justify-center gap-2 sm:flex-row">
            <Link
              href="/lapor"
              className="w-full rounded border border-accent/40 bg-accent/10 px-4 py-2 text-center text-[11px] uppercase tracking-wider text-accent transition-colors hover:bg-accent/20 sm:w-auto"
            >
              Lapor Kejadian
            </Link>
            <Link
              href="/"
              className="w-full rounded border border-base-700 px-4 py-2 text-center text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink sm:w-auto"
            >
              Halaman Muka
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
