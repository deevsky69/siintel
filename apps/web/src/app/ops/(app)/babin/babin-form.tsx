"use client";

import { useActionState, useState } from "react";
import type { BabinRow } from "@/lib/babin";
import { type BabinState, saveBabin } from "./actions";

const IDLE: BabinState = { error: null, done: null };
const field = "w-full rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink";

export function BabinForm({ row, kelurahan }: { row: BabinRow | null; kelurahan: string }) {
  const [state, submit, pending] = useActionState(saveBabin, IDLE);
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="text-xs text-accent underline">
        {row ? "Ubah" : "Isi kontak"}
      </button>
    );
  }
  return (
    <form action={submit} className="mt-2 grid gap-2 sm:grid-cols-3">
      <input type="hidden" name="kelurahan" value={kelurahan} />
      <input name="rank" defaultValue={row?.rank ?? ""} placeholder="Pangkat" className={field} />
      <input
        name="name"
        defaultValue={row?.name ?? ""}
        placeholder="Nama"
        required
        className={`${field} sm:col-span-2`}
      />
      <input
        name="phone_display"
        defaultValue={row?.phone_display ?? ""}
        placeholder="Nomor dinas (tampil ke warga)"
        required
        className={field}
      />
      <input
        name="whatsapp_number"
        defaultValue={row?.whatsapp_number ?? ""}
        placeholder="WhatsApp Babin (62…) untuk buletin"
        className={field}
      />
      <input
        name="telegram_chat_id"
        defaultValue={row?.telegram_chat_id ?? ""}
        placeholder="Chat id grup Telegram (mis. -100…)"
        className={field}
      />
      <input
        name="whatsapp_group_link"
        defaultValue={row?.whatsapp_group_link ?? ""}
        placeholder="Tautan grup WhatsApp (tampil ke warga)"
        className={`${field} sm:col-span-2`}
      />
      <label className="flex items-center gap-1 text-xs text-ink-muted">
        <input type="checkbox" name="is_dummy" defaultChecked={row?.is_dummy ?? false} /> dummy
      </label>
      <div className="flex items-center gap-2 sm:col-span-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded border border-accent/60 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent disabled:opacity-50"
        >
          Simpan
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-ink-faint underline"
        >
          Tutup
        </button>
        {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
        {state.done ? <span className="text-xs text-risk-low">{state.done}</span> : null}
      </div>
    </form>
  );
}
