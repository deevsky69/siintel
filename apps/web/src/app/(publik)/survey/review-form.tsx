"use client";

import { useActionState, useState } from "react";
import { type ReviewSubmitState, submitReview } from "./actions";

const LABELS = ["", "Sangat tidak aman", "Kurang aman", "Biasa saja", "Aman", "Sangat aman"];

/** Formulir ulasan: bintang besar yang mudah diketuk, satu kotak komentar, satu tombol. */
export function ReviewForm({ kecamatan, kelurahan }: { kecamatan: string; kelurahan: string }) {
  const [state, action, pending] = useActionState<ReviewSubmitState, FormData>(submitReview, {
    status: "idle",
  });
  const [rating, setRating] = useState(0);

  if (state.status === "sent") {
    return (
      <div className="rounded-sm bg-risk-low/10 px-4 py-4 text-sm text-ink" role="status">
        <p className="font-semibold text-risk-low">Terima kasih, ulasan Anda diterima.</p>
        <p className="mt-1 text-ink-muted">{state.message}</p>
        <p className="mt-1 text-xs text-ink-faint">Nomor ulasan {state.code}.</p>
      </div>
    );
  }

  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="kecamatan" value={kecamatan} />
      <input type="hidden" name="kelurahan" value={kelurahan} />
      <fieldset>
        <legend className="text-sm font-semibold text-ink">
          Seberapa aman Anda merasa di {kelurahan}?
        </legend>
        <div className="mt-2 flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <label key={n} className="cursor-pointer">
              <input
                type="radio"
                name="rating"
                value={n}
                className="sr-only"
                checked={rating === n}
                onChange={() => setRating(n)}
                required
              />
              <span
                aria-hidden="true"
                className={`block text-4xl leading-none transition ${
                  n <= rating ? "text-[rgb(var(--warga-amber))]" : "text-base-700"
                }`}
              >
                ★
              </span>
              <span className="sr-only">{LABELS[n]}</span>
            </label>
          ))}
          <span className="ml-2 text-sm text-ink-muted">
            {rating ? LABELS[rating] : "Ketuk bintang"}
          </span>
        </div>
      </fieldset>
      <label className="block">
        <span className="text-sm font-semibold text-ink">Ceritakan singkat (boleh kosong)</span>
        <textarea
          name="comment"
          maxLength={300}
          rows={3}
          placeholder="Misal: lampu jalan terang, patroli sering lewat, atau sebaliknya."
          className="mt-1.5 w-full rounded-sm border border-base-800 bg-base-900 px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
        />
      </label>
      {state.status === "error" ? (
        <p className="text-sm text-risk-high" role="alert">
          {state.message}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={pending || rating === 0}
        className="warga-btn warga-btn-primary w-full disabled:opacity-50"
      >
        {pending ? "Mengirim…" : "Kirim ulasan"}
      </button>
      <p className="text-xs leading-relaxed text-ink-faint">
        Anonim: tidak ada nama atau nomor yang disimpan. Ulasan tayang setelah diperiksa moderator
        agar bebas dari identitas orang lain dan kata kasar.
      </p>
    </form>
  );
}
