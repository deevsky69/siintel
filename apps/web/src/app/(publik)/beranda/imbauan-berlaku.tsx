import { getImbauanPublik } from "../lapor/actions";

/**
 * Imbauan yang sedang berlaku, pada halaman muka publik.
 *
 * Komponen terpisah karena ia **async**, sedangkan halaman mukanya tidak boleh menunggu
 * apa pun: pengunjung yang datang untuk melapor harus melihat tombolnya seketika, bahkan
 * ketika API sedang lambat atau mati.
 *
 * Bagian ini tidak melanggar aturan "halaman publik tanpa angka kamtibmas" — ia
 * menegaskannya. Yang tampil hanya baris yang SUDAH melewati keputusan publikasi oleh
 * pemegang `public_alert:publish`. Tidak ada skor, tidak ada cacah kejadian, tidak ada
 * peringkat wilayah, dan wilayahnya disebut setingkat kecamatan.
 */
export async function ImbauanBerlaku() {
  const imbauan = await getImbauanPublik();
  if (imbauan.length === 0) return null;

  return (
    <section className="mt-9 text-left">
      <h2 className="text-2xs uppercase tracking-[0.16em] text-ink-faint">
        Imbauan kewaspadaan yang sedang berlaku
      </h2>
      <ul className="mt-2 space-y-2">
        {imbauan.slice(0, 3).map((row) => (
          <li
            key={row.code}
            className="rounded-lg border border-risk-high/30 bg-risk-high/5 px-4 py-3"
          >
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-heading text-2xs font-semibold uppercase tracking-wider text-risk-high">
                {row.threat_type}
              </span>
              <span className="text-2xs text-ink-muted">{row.area_text}</span>
              {row.time_window ? (
                <span className="text-2xs text-ink-faint">{row.time_window} WIB</span>
              ) : null}
            </div>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">{row.message}</p>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
        Imbauan diterbitkan pejabat berwenang Polres Metro Jakarta Selatan. Ia menyebut wilayah
        setingkat kecamatan dan tidak memuat data rinci.
      </p>
    </section>
  );
}
