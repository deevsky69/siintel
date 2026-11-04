"use client";

import { useActionState, useEffect, useMemo, useState } from "react";
import { Drawer } from "@/components/drawer";
import type { BabinRow } from "@/lib/babin";
import { type BabinState, removeBabin, saveBabin } from "./actions";

/** Satu kelurahan pada master lokasi; kontaknya boleh kosong. */
export type AreaRow = { kelurahan: string; kecamatan: string; polsek: string };

const IDLE: BabinState = { error: null, done: null };

/**
 * Tabel CRUD kontak Babinkamtibmas (4 November 2026, permintaan pemilik proyek: "minimal
 * CRUD/matriks, jangan terlalu banyak teks").
 *
 * Satu baris per kelurahan master lokasi — bukan per kontak — supaya kelurahan yang belum
 * terisi terlihat sebagai kekurangan, bukan hilang dari daftar. Isian dan penghapusan ada
 * di panel samping; tabelnya hanya memuat yang perlu dibaca sekilas.
 */
export function BabinTable({
  areas,
  rows,
  canManage,
}: {
  areas: AreaRow[];
  rows: BabinRow[];
  canManage: boolean;
}) {
  const [query, setQuery] = useState("");
  const [onlyEmpty, setOnlyEmpty] = useState(false);
  const [editing, setEditing] = useState<{ kelurahan: string | null } | null>(null);

  const byKelurahan = useMemo(() => new Map(rows.map((row) => [row.kelurahan, row])), [rows]);
  // Master lokasi gagal dimuat → tetap tampilkan kontak yang ada supaya layar tidak kosong.
  const base: AreaRow[] = useMemo(
    () =>
      areas.length > 0
        ? areas
        : rows.map((row) => ({
            kelurahan: row.kelurahan,
            kecamatan: row.kecamatan,
            polsek: row.polsek,
          })),
    [areas, rows],
  );

  const needle = query.trim().toLowerCase();
  const visible = base.filter((area) => {
    const row = byKelurahan.get(area.kelurahan) ?? null;
    if (onlyEmpty && row) return false;
    if (!needle) return true;
    return [area.kelurahan, area.kecamatan, area.polsek, row?.name ?? "", row?.phone_display ?? ""]
      .join(" ")
      .toLowerCase()
      .includes(needle);
  });
  const filled = base.filter((area) => byKelurahan.has(area.kelurahan)).length;
  const emptyAreas = base.filter((area) => !byKelurahan.has(area.kelurahan));

  return (
    <section className="panel">
      <div className="panel-header">
        <div className="flex items-baseline gap-2">
          <h2 className="panel-title">Babinkamtibmas</h2>
          <span className="rounded bg-base-850 px-1.5 py-0.5 font-mono text-2xs text-ink-muted">
            {filled}/{base.length} kelurahan
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cari kelurahan, nama, nomor…"
            aria-label="Cari kontak"
            className="field w-56"
          />
          <label className="flex items-center gap-1 text-2xs text-ink-muted">
            <input
              type="checkbox"
              checked={onlyEmpty}
              onChange={(event) => setOnlyEmpty(event.target.checked)}
            />
            Belum terisi
          </label>
          {canManage ? (
            <button
              type="button"
              className="btn-sm-primary"
              onClick={() => setEditing({ kelurahan: null })}
            >
              + Tambah
            </button>
          ) : null}
        </div>
      </div>
      <div className="table-scroll max-h-[70vh] overflow-y-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Kelurahan</th>
              <th>Kecamatan</th>
              <th>Polsek</th>
              <th>Babinkamtibmas</th>
              <th>Nomor dinas</th>
              <th>Kanal buletin</th>
              {canManage ? <th className="act">Aksi</th> : null}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={canManage ? 7 : 6} className="py-6 text-center text-ink-faint">
                  Tidak ada kelurahan yang cocok.
                </td>
              </tr>
            ) : (
              visible.map((area) => {
                const row = byKelurahan.get(area.kelurahan) ?? null;
                return (
                  <tr key={area.kelurahan}>
                    <td className="font-heading font-semibold">{area.kelurahan}</td>
                    <td className="text-ink-muted">{area.kecamatan}</td>
                    <td className="text-ink-muted">{area.polsek}</td>
                    <td>
                      {row ? (
                        <span className="inline-flex flex-wrap items-center gap-1.5">
                          <span>
                            {row.rank ? `${row.rank} ` : ""}
                            {row.name}
                          </span>
                          {row.is_dummy ? (
                            <span className="badge bg-risk-moderate/20 text-risk-moderate">
                              Dummy
                            </span>
                          ) : null}
                        </span>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    <td className="font-mono text-ink-muted">{row?.phone_display ?? "—"}</td>
                    <td>
                      {row ? (
                        <span className="inline-flex gap-1">
                          <Chip on={Boolean(row.telegram_chat_id)} label="Telegram" />
                          <Chip on={Boolean(row.whatsapp_number)} label="WA Babin" />
                          <Chip on={Boolean(row.whatsapp_group_link)} label="Grup WA" />
                          <Chip
                            on={Boolean(row.whatsapp_group_chat_id)}
                            label={
                              row.advisory_sent_month
                                ? `Imbauan ${row.advisory_sent_month}`
                                : "Imbauan grup"
                            }
                          />
                        </span>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    {canManage ? (
                      <td className="act">
                        <button
                          type="button"
                          className="btn-sm"
                          onClick={() => setEditing({ kelurahan: area.kelurahan })}
                        >
                          {row ? "Ubah" : "Isi"}
                        </button>
                      </td>
                    ) : null}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {editing ? (
        <BabinDrawer
          kelurahan={editing.kelurahan}
          row={editing.kelurahan ? (byKelurahan.get(editing.kelurahan) ?? null) : null}
          choices={emptyAreas}
          onClose={() => setEditing(null)}
        />
      ) : null}
    </section>
  );
}

function Chip({ on, label }: { on: boolean; label: string }) {
  return (
    <span
      title={on ? `${label}: terpasang` : `${label}: belum`}
      className={`badge ${on ? "bg-accent/15 text-accent" : "bg-base-850 text-ink-faint line-through"}`}
    >
      {label}
    </span>
  );
}

function BabinDrawer({
  kelurahan,
  row,
  choices,
  onClose,
}: {
  /** `null` = tambah baru: kelurahan dipilih dari yang belum terisi. */
  kelurahan: string | null;
  row: BabinRow | null;
  choices: AreaRow[];
  onClose: () => void;
}) {
  const [saveState, save, saving] = useActionState(saveBabin, IDLE);
  const [removeState, remove, removing] = useActionState(removeBabin, IDLE);
  const [confirming, setConfirming] = useState(false);

  // Ditutup setelah tersimpan/terhapus: datanya disegarkan server lewat revalidatePath.
  useEffect(() => {
    if (saveState.done || removeState.done) onClose();
  }, [saveState.done, removeState.done, onClose]);

  const title = row
    ? `Ubah · ${row.kelurahan}`
    : kelurahan
      ? `Isi · ${kelurahan}`
      : "Tambah kontak";
  const formId = "babin-form";

  return (
    <Drawer
      open
      onClose={onClose}
      title={title}
      footer={
        <div className="flex items-center justify-between gap-2">
          <div>
            {row ? (
              confirming ? (
                <form action={remove} className="inline-flex items-center gap-2">
                  <input type="hidden" name="kelurahan" value={row.kelurahan} />
                  <span className="text-2xs text-ink-muted">Hapus kontak ini?</span>
                  <button type="submit" disabled={removing} className="btn-sm-danger">
                    Ya, hapus
                  </button>
                  <button type="button" className="btn-sm" onClick={() => setConfirming(false)}>
                    Batal
                  </button>
                </form>
              ) : (
                <button type="button" className="btn-sm-danger" onClick={() => setConfirming(true)}>
                  Hapus
                </button>
              )
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-sm" onClick={onClose}>
              Batal
            </button>
            <button type="submit" form={formId} disabled={saving} className="btn-sm-primary">
              Simpan
            </button>
          </div>
        </div>
      }
    >
      <form id={formId} action={save} className="space-y-3">
        {kelurahan ? (
          <input type="hidden" name="kelurahan" value={kelurahan} />
        ) : (
          <div>
            <label className="field-label" htmlFor="babin-kelurahan">
              Kelurahan
            </label>
            <select
              id="babin-kelurahan"
              name="kelurahan"
              required
              className="field"
              defaultValue=""
            >
              <option value="" disabled>
                Pilih kelurahan yang belum terisi…
              </option>
              {choices.map((area) => (
                <option key={area.kelurahan} value={area.kelurahan}>
                  {area.kelurahan} · {area.kecamatan}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="field-label" htmlFor="babin-rank">
              Pangkat
            </label>
            <input id="babin-rank" name="rank" defaultValue={row?.rank ?? ""} className="field" />
          </div>
          <div className="col-span-2">
            <label className="field-label" htmlFor="babin-name">
              Nama
            </label>
            <input
              id="babin-name"
              name="name"
              defaultValue={row?.name ?? ""}
              required
              className="field"
            />
          </div>
        </div>
        <div>
          <label className="field-label" htmlFor="babin-phone">
            Nomor dinas <span className="normal-case text-ink-faint">(tampil ke warga)</span>
          </label>
          <input
            id="babin-phone"
            name="phone_display"
            defaultValue={row?.phone_display ?? ""}
            required
            className="field font-mono"
          />
        </div>
        <div>
          <label className="field-label" htmlFor="babin-group">
            Tautan grup WhatsApp{" "}
            <span className="normal-case text-ink-faint">(tampil ke warga)</span>
          </label>
          <input
            id="babin-group"
            name="whatsapp_group_link"
            defaultValue={row?.whatsapp_group_link ?? ""}
            placeholder="https://chat.whatsapp.com/…"
            className="field"
          />
        </div>
        <fieldset className="rounded border border-base-800 p-2.5">
          <legend className="px-1 text-2xs uppercase tracking-wider text-ink-muted">
            Tujuan buletin · tidak tampil ke warga
          </legend>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="field-label" htmlFor="babin-wa">
                WhatsApp Babin
              </label>
              <input
                id="babin-wa"
                name="whatsapp_number"
                defaultValue={row?.whatsapp_number ?? ""}
                placeholder="62…"
                className="field font-mono"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="babin-tg">
                Chat id grup Telegram
              </label>
              <input
                id="babin-tg"
                name="telegram_chat_id"
                defaultValue={row?.telegram_chat_id ?? ""}
                placeholder="-100…"
                className="field font-mono"
              />
            </div>
          </div>
        </fieldset>
        <div>
          <label className="field-label" htmlFor="babin-group-chat">
            Grup WhatsApp warga (imbauan bulanan){" "}
            <span className="normal-case text-ink-faint">terisi lewat /daftar di grup</span>
          </label>
          <input
            id="babin-group-chat"
            name="whatsapp_group_chat_id"
            defaultValue={row?.whatsapp_group_chat_id ?? ""}
            placeholder="…@g.us"
            className="field font-mono"
          />
        </div>
        <label className="flex items-center gap-2 text-xs text-ink-muted">
          <input type="checkbox" name="is_dummy" defaultChecked={row?.is_dummy ?? false} />
          Data dummy (berlabel di layar warga)
        </label>
        {saveState.error ? <p className="text-xs text-risk-critical">{saveState.error}</p> : null}
        {removeState.error ? (
          <p className="text-xs text-risk-critical">{removeState.error}</p>
        ) : null}
      </form>
    </Drawer>
  );
}
