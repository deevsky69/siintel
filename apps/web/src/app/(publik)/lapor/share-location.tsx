"use client";

import { useState } from "react";

type Position = { latitude: number; longitude: number; accuracy: number };

/**
 * Tombol berbagi lokasi.
 *
 * ## Selalu atas permintaan, tidak pernah otomatis
 *
 * Lokasi tidak pernah diminta saat halaman dibuka. Peramban memang akan menampilkan
 * dialog izin, tetapi pelapor yang belum tahu untuk apa lokasinya dipakai hanya punya dua
 * pilihan buruk: menolak sesuatu yang mungkin berguna, atau mengizinkan sesuatu yang tidak
 * ia mengerti. Tombolnya baru ditekan setelah keterangannya dibaca.
 *
 * ## Yang dibagikan adalah titik KEJADIAN
 *
 * Kalimat di bawah tombol menyebutkannya dengan jelas, dan itu bukan sekadar tata bahasa:
 * pelapor yang menekan tombol dari rumahnya sedang mengirimkan letak rumahnya, bukan letak
 * kejadian. Ia berhak tahu itu sebelum menekan, dan berhak membatalkannya sesudahnya.
 */
export function ShareLocation() {
  const [position, setPosition] = useState<Position | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  const ask = () => {
    if (!("geolocation" in navigator)) {
      setError("Peramban ini tidak dapat membagikan lokasi.");
      return;
    }
    setAsking(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (found) => {
        setAsking(false);
        setPosition({
          latitude: found.coords.latitude,
          longitude: found.coords.longitude,
          accuracy: Math.round(found.coords.accuracy),
        });
      },
      (failure) => {
        setAsking(false);
        setError(
          failure.code === failure.PERMISSION_DENIED
            ? "Izin lokasi ditolak. Laporan tetap dapat dikirim tanpa lokasi."
            : "Lokasi tidak dapat diambil. Laporan tetap dapat dikirim tanpa lokasi.",
        );
      },
      // Ketelitian tinggi diminta karena titik yang meleset ratusan meter menunjuk gang yang
      // salah. Batas waktunya pendek supaya pelapor tidak menunggu tanpa kepastian.
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  };

  return (
    <div className="rounded border border-base-800 bg-base-950/40 px-3 py-3">
      <p className="stat-label">Lokasi kejadian (opsional)</p>

      {position ? (
        <>
          <input type="hidden" name="latitude" value={position.latitude} />
          <input type="hidden" name="longitude" value={position.longitude} />
          <input type="hidden" name="accuracy_m" value={position.accuracy} />

          <p className="mt-2 text-xs text-ink">
            Lokasi terlampir —{" "}
            <span className="font-mono">
              {position.latitude.toFixed(5)}, {position.longitude.toFixed(5)}
            </span>{" "}
            <span className="text-ink-muted">(±{position.accuracy} m)</span>
          </p>
          <button
            type="button"
            onClick={() => setPosition(null)}
            className="mt-2 rounded border border-base-700 px-3 py-1.5 text-2xs uppercase tracking-wider text-ink-muted transition-colors hover:border-risk-critical/50 hover:text-risk-critical"
          >
            Hapus lokasi
          </button>
        </>
      ) : (
        <>
          <button
            type="button"
            onClick={ask}
            disabled={asking}
            className="mt-2 rounded border border-accent/40 bg-accent/10 px-3 py-1.5 text-2xs uppercase tracking-wider text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
          >
            {asking ? "Mengambil lokasi…" : "Bagikan lokasi saya"}
          </button>
          <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
            Yang dikirim adalah <strong>titik tempat Anda berada sekarang</strong>, dan itu dicatat
            sebagai lokasi kejadian. Jangan menekannya bila Anda sudah tidak berada di tempat
            kejadian — misalnya bila Anda melapor dari rumah.
          </p>
        </>
      )}

      {error ? (
        <p role="status" className="mt-2 text-2xs leading-relaxed text-risk-high">
          {error}
        </p>
      ) : null}
    </div>
  );
}
