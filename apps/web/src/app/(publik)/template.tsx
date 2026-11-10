/**
 * Dipasang ulang pada setiap perpindahan rute (berbeda dari layout), sehingga animasi
 * masuk `.warga-enter` berjalan lagi tiap kali halaman berganti. Tanpa jarak antar-anak:
 * halaman menyusun bagiannya sendiri (hero selebar layar, lalu blok berpembungkus).
 */
export default function WargaTemplate({ children }: { children: React.ReactNode }) {
  return <div className="warga-enter">{children}</div>;
}
