"use client";

import { useState } from "react";
import type { AttachmentRow } from "@/lib/reports";

const KIND_LABEL: Record<string, string> = {
  IMAGE: "Foto",
  AUDIO: "Suara",
  VIDEO: "Video",
};

/**
 * Lampiran satu laporan masyarakat, dibuka atas permintaan.
 *
 * ## Tidak digambar sampai diminta
 *
 * Isi lampiran adalah data pribadi: wajah orang, suara orang, tempat orang. Menggambarnya
 * pada setiap baris daftar berarti memperlihatkannya kepada siapa pun yang kebetulan
 * melewati layar petugas — termasuk yang tidak sedang menriase laporan itu. Setiap
 * pembukaan juga meninggalkan jejak audit, dan jejak yang tercatat karena daftar tergulir
 * bukan jejak yang berarti apa-apa.
 *
 * ## Berkas yang dimusnahkan tetap disebut
 *
 * Lampiran yang berkasnya sudah dihapus retensi tidak dihilangkan dari daftar; ia
 * ditampilkan beserta tanggal pemusnahannya. Menghilangkannya akan membuat pemeriksa
 * mengira laporan itu memang tidak pernah berlampiran.
 */
export function Attachments({ code, count }: { code: string; count: number }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<AttachmentRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (count === 0) return null;

  const toggle = async () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (rows !== null) return;

    try {
      const response = await fetch(`/api/lampiran/${encodeURIComponent(code)}`);
      if (!response.ok) {
        setError(
          response.status === 403
            ? "Akun Anda tidak berwenang membuka lampiran."
            : "Lampiran tidak dapat dimuat.",
        );
        return;
      }
      const body = (await response.json()) as { data: AttachmentRow[] };
      setRows(body.data);
    } catch {
      setError("Lampiran tidak dapat dimuat.");
    }
  };

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="rounded border border-base-700 px-1.5 py-0.5 text-2xs uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-accent"
      >
        {open ? "Tutup lampiran" : `Lampiran (${count})`}
      </button>

      {open && error ? (
        <p role="alert" className="mt-1.5 text-2xs text-risk-critical">
          {error}
        </p>
      ) : null}

      {open && rows === null && error === null ? (
        <p className="mt-1.5 text-2xs text-ink-faint">Memuat…</p>
      ) : null}

      {open && rows !== null ? (
        <ul className="mt-2 space-y-2">
          {rows.map((row) => (
            <li key={row.attachment_id} className="rounded border border-base-800 p-2">
              <div className="flex items-baseline gap-2">
                <span className="text-2xs uppercase tracking-wider text-accent">
                  {KIND_LABEL[row.kind] ?? row.kind}
                </span>
                <span className="font-mono text-2xs text-ink-faint">
                  {Math.max(1, Math.round(row.byte_size / 1024))} KB
                </span>
                <span className="ml-auto text-2xs text-ink-faint">
                  metadata dilucuti · {row.metadata_stripped_with}
                </span>
              </div>

              {row.available ? (
                <Preview code={code} row={row} />
              ) : (
                <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">
                  Berkas sudah dihapus sesuai masa retensi
                  {row.purged_at ? ` pada ${row.purged_at.slice(0, 10)}` : ""}. Keterangannya
                  dipertahankan sebagai jejak bahwa lampiran ini pernah ada.
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function Preview({ code, row }: { code: string; row: AttachmentRow }) {
  const href = `/api/lampiran/${encodeURIComponent(code)}/${encodeURIComponent(row.attachment_id)}`;

  if (row.kind === "IMAGE") {
    return (
      // Berkas ini dilayani rute terautentikasi milik aplikasi sendiri, bukan aset statis:
      // pengoptimal gambar Next tidak dapat mengambilnya tanpa token, dan memberinya token
      // berarti menyalin data pribadi warga ke cache pengoptimal.
      // biome-ignore lint/performance/noImgElement: alasannya di baris-baris di atas
      <img
        src={href}
        alt={`Lampiran ${KIND_LABEL[row.kind] ?? row.kind} pada laporan ${code}`}
        className="mt-1.5 max-h-64 w-auto rounded border border-base-800"
      />
    );
  }

  // Rekaman dari warga tidak punya teks terjemahan, dan mengarangnya akan menaruh
  // kata-kata yang tidak pernah diucapkan ke dalam berkas bukti.
  if (row.kind === "AUDIO") {
    // biome-ignore lint/a11y/useMediaCaption: lihat catatan di atas.
    return <audio src={href} controls preload="none" className="mt-1.5 w-full" />;
  }

  // biome-ignore lint/a11y/useMediaCaption: lihat catatan di atas.
  return <video src={href} controls preload="none" className="mt-1.5 max-h-64 w-full rounded" />;
}
