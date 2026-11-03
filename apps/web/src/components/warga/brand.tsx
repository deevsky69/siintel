/**
 * Lambang Polri (Tribrata) — berkas resmi berstatus domain publik dari Wikimedia Commons,
 * dikecilkan ke public/brand/. Dipakai di kepala halaman warga, hero, dan halaman masuk.
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

/**
 * "Polri bersama masyarakat", dibuat terlihat: lambang di tengah, dua lingkaran warga
 * mengelilinginya perlahan. Sekadar hiasan bagi pembaca layar (aria-hidden), lambangnya
 * sendiri tetap bergambar.
 */
export function BersamaRing({ size = 168 }: { size?: number }) {
  const dots = [0, 60, 120, 180, 240, 300];
  return (
    <div className="warga-ring" style={{ height: size, width: size }}>
      <div className="warga-ring-orbit" aria-hidden="true">
        {dots.map((deg, index) => (
          <span
            key={deg}
            className={`warga-ring-dot${index % 2 ? " is-amber" : ""}`}
            style={{ transform: `rotate(${deg}deg) translateY(${-size / 2 + 5}px)` }}
          />
        ))}
      </div>
      <div className="warga-ring-orbit is-inner" aria-hidden="true">
        {[30, 150, 270].map((deg) => (
          <span
            key={deg}
            className="warga-ring-dot"
            style={{ transform: `rotate(${deg}deg) translateY(${-(size * 0.36) + 5}px)` }}
          />
        ))}
      </div>
      <div className="warga-ring-emblem" style={{ width: size * 0.56 }}>
        <PolriEmblem size={256} className="h-auto w-full" />
      </div>
    </div>
  );
}
