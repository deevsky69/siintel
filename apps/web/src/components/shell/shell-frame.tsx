"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Topbar } from "./topbar";

/**
 * Kerangka aplikasi: topbar, navigasi, dan isi halaman.
 *
 * ## Mengapa navigasinya satu, bukan dua
 *
 * Layar lebar menampilkan navigasi sebagai kolom tetap; layar sempit menampilkannya sebagai
 * laci yang menutupi halaman. Keduanya **elemen yang sama**, dipindahkan oleh CSS. Menggambar
 * dua salinan akan membuat kelompok menu yang dibuka pengguna di satu salinan tidak terbuka
 * di salinan lainnya — cacat yang baru terlihat saat jendela diubah ukurannya.
 *
 * ## Laci menutup sendiri saat berpindah halaman
 *
 * Tanpa itu, menekan menu di ponsel meninggalkan laci menutupi halaman yang baru saja
 * dibuka, dan pengguna harus menutupnya sendiri untuk melihat apa yang ia minta.
 */
export function ShellFrame({
  name,
  roleName,
  notifications,
  sidebar,
  children,
}: {
  name: string;
  roleName: string;
  notifications?: React.ReactNode;
  sidebar: React.ReactNode;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // `pathname` memang tidak dibaca di dalam efeknya — ia justru PEMICUNYA: berpindah
  // halaman harus menutup laci.
  // biome-ignore lint/correctness/useExhaustiveDependencies: lihat catatan di atas.
  useEffect(() => setOpen(false), [pathname]);

  // Tombol Escape menutup laci. Ia menutupi seluruh halaman, dan sesuatu yang menutupi
  // halaman harus punya jalan keluar yang tidak menuntut membidik tombol kecil.
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  return (
    // `h-dvh`, bukan `h-screen`: di peramban ponsel `100vh` mengabaikan bilah alamat,
    // sehingga bagian bawah halaman terpotong justru di perangkat yang paling sempit.
    <div className="flex h-dvh flex-col overflow-hidden">
      <Topbar
        name={name}
        roleName={roleName}
        notifications={notifications}
        onMenu={() => setOpen(true)}
      />

      <div className="relative flex min-h-0 flex-1">
        {open ? (
          <button
            type="button"
            aria-label="Tutup menu navigasi"
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-30 bg-base-950/70 backdrop-blur-[2px] lg:hidden"
          />
        ) : null}

        <div
          className={`fixed inset-y-0 left-0 z-40 flex w-[240px] pt-14 transition-transform duration-200 ease-out lg:static lg:z-auto lg:w-[208px] lg:translate-x-0 lg:pt-0 ${
            open ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          {sidebar}
        </div>

        <main className="min-w-0 flex-1 overflow-auto p-3 sm:p-4">{children}</main>
      </div>
    </div>
  );
}
