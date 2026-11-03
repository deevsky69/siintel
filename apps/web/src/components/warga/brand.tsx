/**
 * Lambang Polri (Tribrata) — berkas resmi berstatus domain publik dari Wikimedia Commons,
 * dikecilkan ke public/brand/. Dipakai di kepala halaman warga, panel beranda, kaki halaman,
 * dan halaman masuk petugas. Tampil polos — tanpa cincin atau animasi (keputusan pemilik
 * proyek 3 November 2026).
 */
import Image from "next/image";

export function PolriEmblem({ size = 36, className = "" }: { size?: number; className?: string }) {
  const file = size <= 96 ? "polri-96.png" : size <= 256 ? "polri-256.png" : "polri-512.png";
  return (
    <Image
      src={`/brand/${file}`}
      alt="Lambang Polri"
      width={size}
      height={size}
      unoptimized
      className={className}
    />
  );
}
