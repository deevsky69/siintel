"use client";

import { useEffect, useState } from "react";

const DATE_FORMAT = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "Asia/Jakarta",
});

const TIME_FORMAT = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: "Asia/Jakarta",
});

/**
 * Jam WIB pada topbar.
 *
 * Waktu disimpan UTC di database dan ditampilkan WIB (docs/02 K-3), sehingga zona
 * ditetapkan eksplisit di sini — bukan mengikuti zona perangkat yang membuka halaman.
 *
 * Render pertama sengaja kosong agar markup server dan klien sama; tanpa itu, jam
 * akan berbeda antara keduanya dan React melaporkan hydration mismatch.
 */
export function Clock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-baseline gap-3 font-mono text-sm text-ink-muted">
      <span suppressHydrationWarning>{now ? DATE_FORMAT.format(now) : "—"}</span>
      <span className="text-ink" suppressHydrationWarning>
        {now ? `${TIME_FORMAT.format(now)} WIB` : "--:--:-- WIB"}
      </span>
    </div>
  );
}
