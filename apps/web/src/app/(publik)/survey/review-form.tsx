"use client";

import { useActionState, useState } from "react";
import { type ReviewSubmitState, submitReview } from "./actions";

const LABELS = ["", "Sangat tidak aman", "Kurang aman", "Biasa saja", "Aman", "Sangat aman"];

/**
 * Formulir ulasan (mockup 10 November 2026): lima kotak bintang selebar formulir yang mudah
 * diketuk, satu kotak komentar, satu tombol navy. Setelah terkirim: kotak navy "OK", judul,
 * dan tombol "Nilai kelurahan lain".
 */
export function ReviewForm({ kecamatan, kelurahan }: { kecamatan: string; kelurahan: string }) {
  const [state, action, pending] = useActionState<ReviewSubmitState, FormData>(submitReview, {
    status: "idle",
  });
  const [rating, setRating] = useState(0);

  if (state.status === "sent") {
    return (
      <div className="flex flex-col items-start gap-4 py-2" role="status">
        <span className="inline-flex h-16 w-16 items-center justify-center bg-[rgb(var(--warga-navy))] text-[22px] font-medium text-[rgb(var(--warga-goldl))]">
          OK
        </span>
        <h2 className="text-[28px] text-[rgb(var(--warga-navy))]">Ulasan Anda telah diterima</h2>
        <p className="text-base leading-relaxed text-ink-faint">{state.message}</p>
        <p className="text-xs text-ink-faint">Nomor ulasan {state.code}.</p>
        <a href="/survey" className="warga-btn warga-btn-sm warga-btn-ghost">
          Nilai kelurahan lain
        </a>
      </div>
    );
  }

  return (
    <form action={action} className="flex flex-col gap-6">
      <input type="hidden" name="kecamatan" value={kecamatan} />
      <input type="hidden" name="kelurahan" value={kelurahan} />
      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-3.5 p-0 text-lg font-extrabold text-[rgb(var(--warga-navy))]">
          Seberapa aman Anda merasa di {kelurahan}?
        </legend>
        <div className="grid grid-cols-5 gap-2.5" role="radiogroup" aria-label="Nilai 1 sampai 5">
          {[1, 2, 3, 4, 5].map((n) => (
            <label
              key={n}
              className={`warga-option relative items-center text-center ${n <= rating ? "is-on" : ""}`}
            >
              <input
                type="radio"
                name="rating"
                value={n}
                checked={rating === n}
                onChange={() => setRating(n)}
                required
              />
              <span
                aria-hidden="true"
                className={`text-[30px] leading-none ${n <= rating ? "text-[rgb(var(--warga-gold))]" : "text-base-700"}`}
              >
                ★
              </span>
              <span className="text-xs font-semibold leading-tight">{LABELS[n]}</span>
            </label>
          ))}
        </div>
        <p className="mt-2 text-[13px] text-ink-faint">
          {rating ? `Anda memilih: ${LABELS[rating]}` : "Ketuk salah satu bintang."}
        </p>
      </fieldset>
      <label className="flex flex-col gap-1.5">
        <span className="warga-label">
          Ceritakan singkat <span className="font-medium text-ink-faint">(boleh kosong)</span>
        </span>
        <textarea
          name="comment"
          maxLength={300}
          rows={4}
          placeholder="Misal: lampu jalan terang, patroli sering lewat, atau sebaliknya."
          className="warga-field"
        />
        <span className="warga-help">Maksimal 300 karakter.</span>
      </label>
      {state.status === "error" ? (
        <p className="warga-error" role="alert">
          {state.message}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-base-850 pt-5">
        <p className="warga-help flex-[1_1_360px]">
          Anonim: tidak ada nama atau nomor yang disimpan. Ulasan tayang setelah diperiksa moderator
          agar bebas dari identitas orang lain dan kata kasar.
        </p>
        <button
          type="submit"
          disabled={pending || rating === 0}
          className="warga-btn warga-btn-primary min-h-[52px] px-7 disabled:opacity-50"
        >
          {pending ? "Mengirim…" : "Kirim ulasan"}
        </button>
      </div>
    </form>
  );
}
