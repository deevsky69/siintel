import { Suspense } from "react";
import { LoginForm } from "./login-form";

export const metadata = { title: "Masuk — PREDIKSI PRESISI" };

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
      </div>
    </div>
  );
}
