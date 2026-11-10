"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { safeNextPath } from "@/lib/navigation";

/**
 * Formulir masuk (mockup 10 November 2026): isian bergaris emas yang mengisi dari kiri saat
 * difokus, tombol navy yang tersapu emas saat disentuh, tombol lihat/sembunyikan sandi.
 *
 * Kredensial dikirim ke route handler Next.js, yang meneruskannya ke backend dan menyimpan
 * token pada cookie httpOnly. Token tidak pernah menyentuh kode klien.
 */
export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: String(form.get("username") ?? ""),
        password: String(form.get("password") ?? ""),
      }),
    });

    if (response.ok) {
      // Hanya lintasan relatif satu origin yang diterima — lihat lib/navigation.ts.
      router.replace(safeNextPath(params.get("lanjut")));
      router.refresh();
      return;
    }

    const body = await response.json().catch(() => null);
    setError(body?.error?.message ?? "Tidak dapat masuk. Periksa kembali kredensial.");
    setBusy(false);
  }

  return (
    <form onSubmit={submit} noValidate>
      {error ? (
        <p role="alert" className="warga-error mb-4">
          {error}
        </p>
      ) : null}

      <div className="mb-4">
        <label htmlFor="masuk-username" className="warga-label mb-1.5 text-[13px]">
          Username
        </label>
        <div className="warga-inp">
          <input
            id="masuk-username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            className="warga-field text-base"
          />
        </div>
      </div>

      <div className="mb-4">
        <label htmlFor="masuk-password" className="warga-label mb-1.5 text-[13px]">
          Password
        </label>
        <div className="warga-inp">
          <input
            id="masuk-password"
            name="password"
            type={shown ? "text" : "password"}
            autoComplete="current-password"
            required
            className="warga-field pr-11 text-base"
          />
          <button
            type="button"
            onClick={() => setShown((value) => !value)}
            aria-label={shown ? "Sembunyikan password" : "Tampilkan password"}
            aria-pressed={shown}
            className="absolute bottom-0.5 right-0.5 top-0.5 grid w-[42px] place-items-center text-ink-faint aria-pressed:text-[rgb(var(--warga-navy))]"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden="true"
            >
              <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
              <circle cx="12" cy="12" r="3" />
              {shown ? <path d="M4 4l16 16" /> : null}
            </svg>
          </button>
        </div>
      </div>

      <button type="submit" disabled={busy} className="masuk-btn">
        <span>{busy ? "Memeriksa…" : "Masuk"}</span>
      </button>
    </form>
  );
}
