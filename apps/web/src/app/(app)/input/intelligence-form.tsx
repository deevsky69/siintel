"use client";

import { useActionState } from "react";
import { recordIntelligence } from "./actions";
import { EntryFeedback } from "./entry-feedback";
import { ENTRY_IDLE } from "./entry-state";
import { type Choice, FIELD, HINT, type LocationGroup, SUBMIT } from "./options";

/**
 * Formulir pencatatan laporan intelijen.
 *
 * Bidangnya mengikuti tabel `intelligence_reports` apa adanya: tanggal, kategori
 * kerawanan, wilayah, keandalan sumber, tingkat keyakinan, urgensi, dampak, dan status
 * tindak lanjut. Tabel itu memang **tidak** memiliki kolom uraian bebas — menambahkannya
 * adalah perubahan schema, bukan bagian dari formulir ini.
 *
 * Kategori kerawanan diketik, bukan dipilih dari daftar tertutup: taksonomi kategori
 * intelijen belum ada di `config/taxonomy/mappings.yaml`, dan mengarang daftarnya di
 * layar akan melahirkan taksonomi yang tidak pernah disetujui siapa pun. Yang ditawarkan
 * adalah kategori yang sudah dipakai pada data.
 */
export function IntelligenceForm({
  statuses,
  impacts,
  locations,
  categories,
  reliabilities,
  maxDate,
  demoClock,
}: {
  statuses: Choice[];
  impacts: Choice[];
  locations: LocationGroup[];
  categories: string[];
  reliabilities: string[];
  maxDate: string;
  demoClock: boolean;
}) {
  const [state, submit, pending] = useActionState(recordIntelligence, ENTRY_IDLE);

  return (
    <form action={submit}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="stat-label">Kategori Kerawanan</span>
          <input
            name="category"
            required
            maxLength={100}
            list="daftar-kategori-intelijen"
            className={FIELD}
            placeholder="mis. Kerawanan Lokasi"
          />
          <datalist id="daftar-kategori-intelijen">
            {categories.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
          <span className={HINT}>
            {categories.length > 0
              ? "Saran diambil dari kategori yang sudah dipakai pada data dalam cakupan akun Anda."
              : "Belum ada kategori yang dapat disarankan untuk akun Anda; isi apa adanya."}
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
        </label>

        <label className="block">
          <span className="stat-label">Tanggal Laporan</span>
          <input type="date" name="report_date" required max={maxDate} className={FIELD} />
          <span className={HINT}>
            {demoClock
              ? `Dibatasi sampai ${maxDate} — waktu acuan aplikasi pada dataset demo, bukan jam dinding.`
              : "Laporan bertanggal di masa depan ditolak."}
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Keandalan Sumber</span>
          <input name="reliability" list="daftar-keandalan" maxLength={10} className={FIELD} />
          <datalist id="daftar-keandalan">
            {reliabilities.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
          <span className={HINT}>
            Skala keandalan sumber belum ditetapkan sebagai taksonomi; dataset memakai A/B/C.
          </span>
        </label>

        <label className="block">
          <span className="stat-label">Tingkat Keyakinan (0–100)</span>
          <input type="number" name="confidence" min={0} max={100} className={FIELD} />
        </label>

        <label className="block">
          <span className="stat-label">Urgensi (0–100)</span>
          <input type="number" name="urgency" min={0} max={100} className={FIELD} />
        </label>

        <label className="block">
          <span className="stat-label">Perkiraan Dampak</span>
          <select name="impact" defaultValue="" className={FIELD}>
            <option value="">Tidak dinilai</option>
            {impacts.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="stat-label">Status Tindak Lanjut</span>
          <select name="status" defaultValue="" className={FIELD}>
            <option value="">Baru (bawaan)</option>
            {statuses.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <EntryFeedback state={state} noun="Laporan intelijen" />

      <button type="submit" disabled={pending} className={SUBMIT}>
        {pending ? "Menyimpan…" : "Catat Laporan Intelijen"}
      </button>

      <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
        Laporan intelijen tidak menyimpan identitas sumber maupun orang yang dilaporkan. Yang
        tersimpan adalah kerawanan pada satu wilayah, bukan penilaian terhadap individu (CLAUDE.md
        §10, §16).
      </p>
    </form>
  );
}
