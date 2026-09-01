"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

/**
 * Formulir masuk.
 *
 * Kredensial dikirim ke route handler Next.js, yang meneruskannya ke backend dan
 * menyimpan token pada cookie httpOnly. Token tidak pernah menyentuh kode klien.
 */
export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      router.replace(params.get("lanjut") || "/");
      router.refresh();
      return;
    }

    const body = await response.json().catch(() => null);
    setError(body?.error?.message ?? "Tidak dapat masuk. Periksa kembali kredensial.");
    setBusy(false);
  }

  return (
    <form onSubmit={submit} className="panel p-5">
      <label className="block">
        <span className="stat-label">Username</span>
        <input
          name="username"
          autoComplete="username"
          required
          className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
        />
      </label>

      <label className="mt-4 block">
        <span className="stat-label">Password</span>
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
        />
      </label>

      {error ? (
        <p role="alert" className="mt-4 text-xs text-risk-critical">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={busy}
        className="mt-5 w-full rounded bg-accent/20 px-4 py-2 font-heading text-sm font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-50"
      >
        {busy ? "Memeriksa…" : "Masuk"}
      </button>
    </form>
  );
}
