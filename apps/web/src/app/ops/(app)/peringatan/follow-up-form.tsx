"use client";

import { useActionState, useState } from "react";
import type { WarningAction } from "@/lib/warnings";
import { type FollowUpState, followUp } from "./actions";

/**
 * Formulir tindak lanjut peringatan dini.
 *
 * Tombol yang ditawarkan ditentukan pemanggil: hanya transisi yang masih sah menurut
 * status **dan** yang kewenangannya dimiliki pengguna. Penyaringan itu sekadar
 * kenyamanan — backend tetap yang menolak, dan penolakannya ditampilkan di sini
 * (CLAUDE.md §21).
 *
 * Peringatan bukan perintah: yang direkam tombol ini adalah siapa yang menerima dan
 * siapa yang menutup peringatan, bukan penugasan operasional (CLAUDE.md §13).
 */

/**
 * Label tombol ditulis di berkas klien ini, bukan diimpor dari `@/lib/warnings`:
 * modul itu menarik `@/lib/api` yang memuat `next/headers`, dan komponen `"use client"`
 * tidak boleh memuatnya — `next build` akan gagal. Tipe `WarningAction` aman karena
 * diimpor sebagai `import type` dan hilang saat kompilasi.
 */
const LABELS: Record<WarningAction, { idle: string; busy: string; done: string; tone: string }> = {
  acknowledge: {
    idle: "Terima Peringatan",
    busy: "Mencatat…",
    done: "diterima",
    tone: "border-accent/50 text-accent hover:bg-accent/10",
  },
  resolve: {
    idle: "Nyatakan Selesai",
    busy: "Mencatat…",
    done: "dinyatakan selesai",
    tone: "border-risk-low/50 text-risk-low hover:bg-risk-low/10",
  },
};

/**
 * Keadaan awal formulir. Ditulis di sini karena berkas `"use server"` hanya boleh
 * mengekspor fungsi async; mengekspornya dari `actions.ts` membuat Next menolak modul
 * itu saat action dipanggil.
 */
const IDLE: FollowUpState = { error: null, done: null };

export function FollowUpForm({ code, offers }: { code: string; offers: WarningAction[] }) {
  const [state, submit, pending] = useActionState(followUp, IDLE);
  const [pressed, setPressed] = useState<WarningAction | null>(null);

  return (
    <form action={submit}>
      <input type="hidden" name="code" value={code} />

      <div className="flex gap-2">
        {offers.map((action) => (
          <button
            key={action}
            type="submit"
            name="action"
            value={action}
            disabled={pending}
            onClick={() => setPressed(action)}
            className={`flex-1 rounded border bg-base-850 px-3 py-2 font-heading text-xs font-semibold uppercase tracking-wider transition disabled:opacity-40 ${LABELS[action].tone}`}
          >
            {pending && pressed === action ? LABELS[action].busy : LABELS[action].idle}
          </button>
        ))}
      </div>

      {state.error ? (
        <p role="alert" className="mt-3 text-xs leading-relaxed text-risk-critical">
          {state.error}
        </p>
      ) : null}

      {state.done ? (
        <p role="status" className="mt-3 text-xs leading-relaxed text-risk-low">
          Peringatan <span className="font-mono">{state.done.code}</span>{" "}
          {LABELS[state.done.action].done} atas nama akun Anda.
        </p>
      ) : null}

      <p className="mt-2 text-2xs leading-relaxed text-ink-muted">
        Tindak lanjut tercatat beserta nama petugas dan waktunya pada jejak audit.
      </p>
    </form>
  );
}
