/**
 * Dipasang ulang pada setiap perpindahan rute (berbeda dari layout), sehingga animasi
 * masuk `.warga-enter` berjalan lagi tiap kali halaman berganti.
 */
export default function WargaTemplate({ children }: { children: React.ReactNode }) {
  return <div className="warga-enter space-y-5">{children}</div>;
}
