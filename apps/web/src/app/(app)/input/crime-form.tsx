"use client";

import { useActionState } from "react";
import { recordCrime } from "./actions";
import { EntryFeedback } from "./entry-feedback";
import { ENTRY_IDLE } from "./entry-state";
import { type Choice, FIELD, HINT, type LocationGroup, SUBMIT } from "./options";

/**
 * Formulir pencatatan kejadian kriminal.
 *
 * Bidangnya mengikuti spesifikasi §6.1 — jenis, tanggal, jam, wilayah, kategori TKP,
 * modus, sasaran, dan status penanganan.
 *
 * **Tidak ada isian identitas, dan itu disengaja.** Spesifikasi §6.1 menyatakan identitas
 * korban/pelaku/saksi tidak diperlukan untuk PoC, dan `crime_incidents` memang tidak
 * memiliki kolomnya (CLAUDE.md §16). Ketiadaannya dinyatakan di layar supaya terbaca
 * sebagai keputusan, bukan sebagai bidang yang lupa dibuat.
 *
 * Wilayah tidak diketik: dipilih dari `GET /locations`, sehingga setiap kejadian terikat
 * pada satu sel grid yang benar-benar ada. Polsek/kecamatan/kelurahan tidak diminta —
 * seluruhnya diperoleh dari sel itu (docs/02 K-8).
 */
export function CrimeForm({
  incidentTypes,
  statuses,
  locations,
  locationTypes,
  modusOptions,
  targetTypes,
  maxDate,
  demoClock,
}: {
  incidentTypes: Choice[];
  statuses: Choice[];
  locations: LocationGroup[];
  locationTypes: string[];
  modusOptions: string[];
  targetTypes: string[];
  /** Tanggal terakhir yang masuk akal menurut waktu acuan aplikasi. */
  maxDate: string;
  demoClock: boolean;
}) {
  const [state, submit, pending] = useActionState(recordCrime, ENTRY_IDLE);

  return (
    <form action={submit}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="stat-label">Jenis Kejadian</span>
          <select name="incident_type" required defaultValue="" className={FIELD}>
            <option value="" disabled>
              Pilih jenis kejadian…
            </option>
            {incidentTypes.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <span className={HINT}>
            Daftar ini berasal dari `config/taxonomy/mappings.yaml`. Jenis di luar daftar ditolak
            backend — taksonomi tidak boleh bertambah lewat formulir.
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Wilayah / Sel Grid</span>
          <select name="location_code" required defaultValue="" className={FIELD}>
            <option value="" disabled>
              Pilih wilayah…
            </option>
            {locations.map((group) => (
              <optgroup key={group.polsek} label={group.polsek}>
                {group.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <span className={HINT}>
            Dikelompokkan menurut Polsek. Akun yang dibatasi wilayah hanya dapat menulis di
            polseknya sendiri; sel di luar itu dijawab "tidak ditemukan" oleh backend.
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Tanggal Kejadian</span>
          <input type="date" name="incident_date" required max={maxDate} className={FIELD} />
          <span className={HINT}>
            {demoClock
              ? `Dibatasi sampai ${maxDate} — waktu acuan aplikasi pada dataset demo, bukan jam dinding. Kejadian yang belum terjadi tidak dicatat sebagai fakta.`
              : "Kejadian yang belum terjadi tidak dicatat sebagai fakta."}
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Jam Kejadian (WIB)</span>
          <input type="time" name="incident_time" required className={FIELD} />
        </label>

        <label className="block">
          <span className="stat-label">Kategori TKP</span>
          <input
            name="location_type"
            list="daftar-kategori-tkp"
            className={FIELD}
            placeholder="mis. Jalan, Permukiman"
          />
          <datalist id="daftar-kategori-tkp">
            {locationTypes.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
          <span className={HINT}>
            Saran diambil dari kategori yang sudah dipakai pada data. Nilai baru diterima —
            taksonomi kategori TKP memang belum ditetapkan (U-16).
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Status Penanganan</span>
          <select name="status" defaultValue="" className={FIELD}>
            <option value="">Dilaporkan (bawaan)</option>
            {statuses.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="stat-label">Modus</span>
          <input name="modus" list="daftar-modus" className={FIELD} />
          <datalist id="daftar-modus">
            {modusOptions.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
        </label>

        <label className="block">
          <span className="stat-label">Sasaran</span>
          <input name="target_type" list="daftar-sasaran" className={FIELD} />
          <datalist id="daftar-sasaran">
            {targetTypes.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
        </label>
      </div>

      <EntryFeedback state={state} noun="Kejadian" />

      <button type="submit" disabled={pending} className={SUBMIT}>
        {pending ? "Menyimpan…" : "Catat Kejadian"}
      </button>

      <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
        Formulir ini <strong>tidak meminta identitas korban, pelaku, maupun saksi</strong>. Data itu
        tidak diperlukan untuk prototipe (spesifikasi §6.1) dan tabelnya memang tidak memiliki
        kolomnya. Pencatatan tersimpan beserta nama petugas dan waktunya di audit trail.
      </p>
    </form>
  );
}
