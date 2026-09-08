"use client";

import { useId, useState } from "react";
import type { ReportOptions } from "./actions";
import { uploadAttachment } from "./actions";

type Attached = { handle: string; name: string; kind: string; byteSize: number };

const KIND_LABEL: Record<string, string> = {
  IMAGE: "Foto",
  AUDIO: "Suara",
  VIDEO: "Video",
};

/**
 * Melampirkan foto, rekaman suara, atau video.
 *
 * ## Berkas diunggah saat dipilih, bukan saat formulir dikirim
 *
 * Pelapor tahu berkasnya diterima atau ditolak **sebelum** ia menulis keterangan. Bila
 * unggahan digabungkan dengan pengiriman, satu berkas yang terlalu besar akan menolak
 * seluruh laporan setelah semuanya diketik — dan pada koneksi ponsel yang lambat,
 * setelah menunggu lama.
 *
 * Yang tersimpan di formulir hanyalah **handle**: rahasia acak yang menunjuk berkas yang
 * sudah bersih di server. Berkasnya sendiri tidak pernah dikirim dua kali.
 *
 * ## Peringatan yang ditulis di sini bukan basa-basi
 *
 * Foto ponsel membawa koordinat GPS di dalam berkasnya. Metadata itu dilucuti server
 * sebelum disimpan, dan pelapor diberi tahu — tetapi yang tidak dapat dilucuti siapa pun
 * adalah **wajah orang di dalam fotonya**. Itu keputusan pelapor, dan ia perlu
 * mengetahuinya sebelum memilih berkas.
 */
export function AttachFiles({ options }: { options: ReportOptions }) {
  const inputId = useId();
  const [files, setFiles] = useState<Attached[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const megabytes = Math.round(options.max_attachment_bytes / (1024 * 1024));
  const full = files.length >= options.max_attachments;

  const choose = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = Array.from(event.target.files ?? []);
    // Kolom dikosongkan lebih dulu supaya memilih berkas yang sama dua kali tetap memicu
    // perubahan — tanpa ini, mencoba ulang setelah gagal tidak menghasilkan apa pun.
    event.target.value = "";
    if (chosen.length === 0) return;

    setError(null);
    setBusy(true);
    const accepted: Attached[] = [];

    for (const file of chosen) {
      if (files.length + accepted.length >= options.max_attachments) {
        setError(`Paling banyak ${options.max_attachments} berkas.`);
        break;
      }
      // Diperiksa di peramban lebih dulu supaya berkas besar tidak dikirim sia-sia lewat
      // jaringan ponsel. Server tetap memeriksanya sendiri — ini kenyamanan, bukan pengaman.
      if (file.size > options.max_attachment_bytes) {
        setError(`${file.name} melebihi batas ${megabytes} MB.`);
        continue;
      }

      const payload = new FormData();
      payload.append("berkas", file);
      const result = await uploadAttachment(payload);

      if (result.status === "error") {
        setError(`${file.name}: ${result.message}`);
        continue;
      }
      accepted.push({
        handle: result.handle,
        name: file.name,
        kind: result.kind,
        byteSize: result.byteSize,
      });
    }

    setFiles((previous) => [...previous, ...accepted]);
    setBusy(false);
  };

  return (
    <div className="rounded border border-base-800 bg-base-950/40 px-3 py-3">
      <p className="stat-label">Foto, suara, atau video (opsional)</p>

      <ul className="mt-2 space-y-1">
        {files.map((file) => (
          <li key={file.handle} className="flex items-baseline gap-2 text-xs">
            <input type="hidden" name="attachments" value={file.handle} />
            <span className="shrink-0 text-2xs uppercase tracking-wider text-accent">
              {KIND_LABEL[file.kind] ?? file.kind}
            </span>
            <span className="min-w-0 truncate text-ink">{file.name}</span>
            <span className="ml-auto shrink-0 font-mono text-2xs text-ink-faint">
              {Math.max(1, Math.round(file.byteSize / 1024))} KB
            </span>
            <button
              type="button"
              onClick={() => setFiles((rest) => rest.filter((row) => row.handle !== file.handle))}
              aria-label={`Hapus ${file.name}`}
              className="shrink-0 rounded border border-base-700 px-1.5 text-2xs text-ink-muted transition-colors hover:border-risk-critical/50 hover:text-risk-critical"
            >
              Hapus
            </button>
          </li>
        ))}
      </ul>

      <label
        htmlFor={inputId}
        className={`mt-2 inline-block rounded border px-3 py-1.5 text-2xs uppercase tracking-wider transition-colors ${
          full || busy
            ? "cursor-not-allowed border-base-800 text-ink-faint"
            : "cursor-pointer border-accent/40 bg-accent/10 text-accent hover:bg-accent/20"
        }`}
      >
        {busy ? "Mengunggah…" : full ? "Sudah penuh" : "Pilih berkas"}
      </label>
      <input
        id={inputId}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,audio/mpeg,audio/ogg,video/mp4,video/webm"
        disabled={full || busy}
        onChange={choose}
        className="sr-only"
      />

      <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
        Paling banyak {options.max_attachments} berkas, masing-masing {megabytes} MB.{" "}
        {options.attachment_basis}
      </p>
      <p className="mt-1 text-2xs leading-relaxed text-ink-faint">
        <strong>Metadata berkas dihapus, wajah tidak.</strong> Koordinat dan merek kamera yang
        ditanam ponsel di dalam berkas dilucuti sebelum disimpan — tetapi orang yang terlihat di
        dalam foto atau terdengar di dalam rekaman tetap dapat dikenali.
      </p>

      {error ? (
        <p role="alert" className="mt-2 text-2xs leading-relaxed text-risk-critical">
          {error}
        </p>
      ) : null}
    </div>
  );
}
