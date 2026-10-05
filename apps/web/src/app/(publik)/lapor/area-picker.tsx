"use client";

import { useState } from "react";
import { type AreaOption, nearestArea } from "./area-nearest";
import { type Position, ShareLocation } from "./share-location";

/**
 * Pemilih wilayah laporan: kecamatan → kelurahan, dengan lokasi peramban sebagai pembantu.
 *
 * Permintaan pemilik proyek 5 Oktober 2026: laporan dari laptop/komputer pun harus
 * membawa wilayah sekurang-kurangnya setingkat kelurahan. Dua jalan yang saling menutup:
 *
 * - **Memilih sendiri.** Kelurahan adalah pilihan, bukan isian bebas, supaya nilainya
 *   selalu cocok dengan master lokasi dan laporan langsung terhubung ke peta kelurahan.
 * - **Membagikan lokasi.** Peramban laptop memberi lokasi kasar dari Wi-Fi/IP. Dari titik
 *   itu kelurahan terdekat DIUSULKAN dan terisi otomatis — pelapor tetap dapat mengubahnya,
 *   dan layar menyebut bahwa itu usulan beserta jaraknya.
 *
 * Kelurahan tetap opsional: laporan yang hanya menyebut kecamatan tetap sah, dan backend
 * yang menentukan wilayah akhirnya (CLAUDE.md §21).
 */
export function AreaPicker({
  areas,
  kecamatanList,
}: {
  areas: AreaOption[];
  kecamatanList: string[];
}) {
  const [kecamatan, setKecamatan] = useState("");
  const [kelurahan, setKelurahan] = useState("");
  const [suggested, setSuggested] = useState<{ kelurahan: string; distanceM: number } | null>(null);

  const kelurahanOptions = areas.find((area) => area.kecamatan === kecamatan)?.kelurahan ?? [];

  const onPosition = (position: Position | null) => {
    if (position === null) {
      setSuggested(null);
      return;
    }
    const nearest = nearestArea(areas, position);
    if (nearest === null) return;
    setKecamatan(nearest.kecamatan);
    setKelurahan(nearest.kelurahan);
    setSuggested({ kelurahan: nearest.kelurahan, distanceM: Math.round(nearest.distanceM) });
  };

  const select =
    "mt-1 w-full rounded border border-base-700 bg-base-950 px-3 py-2 text-sm text-ink focus:border-accent/60 focus:outline-none";

  return (
    <div className="space-y-4">
      <label className="block">
        <span className="stat-label">Kecamatan</span>
        <select
          name="kecamatan"
          required
          value={kecamatan}
          onChange={(event) => {
            setKecamatan(event.target.value);
            setKelurahan("");
            setSuggested(null);
          }}
          className={select}
        >
          <option value="" disabled>
            Pilih kecamatan
          </option>
          {kecamatanList.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="stat-label">Kelurahan (bila tahu)</span>
        <select
          name="kelurahan"
          value={kelurahan}
          onChange={(event) => {
            setKelurahan(event.target.value);
            setSuggested(null);
          }}
          disabled={kecamatan === ""}
          className={select}
        >
          <option value="">
            {kecamatan === "" ? "Pilih kecamatan lebih dahulu" : "Tidak tahu / lewati"}
          </option>
          {kelurahanOptions.map((option) => (
            <option key={option.name} value={option.name}>
              {option.name}
            </option>
          ))}
        </select>
        {suggested ? (
          <span className="mt-1 block text-2xs leading-relaxed text-ink-muted">
            Terisi otomatis dari lokasi Anda:{" "}
            <span className="text-ink">{suggested.kelurahan}</span> (sekitar{" "}
            {suggested.distanceM.toLocaleString("id-ID")} m dari titik pusat kelurahan). Ubah bila
            keliru — lokasi peramban di laptop bisa meleset ratusan meter.
          </span>
        ) : (
          <span className="mt-1 block text-2xs leading-relaxed text-ink-faint">
            Kelurahan membantu petugas menempatkan laporan di peta kelurahan. Bila Anda membagikan
            lokasi, kelurahan terdekat terisi otomatis.
          </span>
        )}
      </label>

      <ShareLocation onPosition={onPosition} />
    </div>
  );
}
