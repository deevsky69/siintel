import Link from "next/link";
import { Panel } from "@/components/panel";
import { getScoringConfig } from "@/lib/scoring";

export const dynamic = "force-dynamic";

/**
 * Pengaturan Sistem — konfigurasi yang sedang berlaku (TASK 161).
 *
 * **Hanya membaca.** Bobot dan ambang hidup di `config/risk/`, dan diubah lewat berkas
 * lalu pembangunan ulang image — bukan lewat layar ini. Itu bukan keterbatasan yang belum
 * sempat diperbaiki, melainkan syarat ketertelusuran: setiap baris `risk_scores` menyimpan
 * `weights_version`, dan versi yang masih dirujuk baris mana pun tidak boleh berubah isinya
 * (CLAUDE.md §11, §12). Formulir yang dapat menyunting bobot langsung dari layar akan
 * membuat skor lama tampak terbit di bawah aturan yang tidak pernah berlaku saat itu.
 *
 * Yang dikerjakan layar ini adalah membuat konfigurasi itu **terlihat**: angka yang tidak
 * dapat dikembalikan ke aturan yang menghasilkannya tidak dapat diperdebatkan siapa pun.
 */
export default async function PengaturanPage() {
  const config = await getScoringConfig();

  return (
    <div className="space-y-3">
      <Panel
        title="Versi Konfigurasi yang Berlaku"
        action={
          <span className="text-2xs uppercase tracking-wider text-ink-faint">
            {config.active_status}
          </span>
        }
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Versi Bobot" value={config.active_version} />
          <Stat label="Versi Ambang" value={config.thresholds.version} />
          <Stat label="Status Ambang" value={config.thresholds.status} />
          <Stat label="Sel Lokasi" value={String(config.coverage.locations)} />
        </div>

        <p className="mt-3 text-2xs leading-relaxed text-ink-faint">{config.config_basis}</p>
      </Panel>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Panel title="Kelas Risiko">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-2xs uppercase tracking-wider text-ink-faint">
                <th className="pb-1 font-normal">Kelas</th>
                <th className="pb-1 text-right font-normal">Rentang Skor</th>
              </tr>
            </thead>
            <tbody>
              {config.thresholds.risk_classes.map((band) => (
                <tr key={band.class} className="border-t border-base-800">
                  <td className="py-1.5 text-ink">{band.class}</td>
                  <td className="py-1.5 text-right font-mono text-ink-muted">
                    {band.min}–{band.max}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-2xs leading-relaxed text-ink-faint">
            Ambang ini berstatus <strong>{config.thresholds.status}</strong> dan belum ditetapkan
            SOP mana pun. Ia hidup di satu berkas konfigurasi, bukan tersebar di kode — sehingga
            penetapan resminya cukup mengubah satu tempat.
          </p>
        </Panel>

        <Panel title="Jendela Waktu Penilaian">
          <ul className="space-y-1">
            {config.time_windows.map((window) => (
              <li key={window} className="border-t border-base-800 py-1.5 first:border-t-0">
                <span className="font-mono text-xs text-ink">{window}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-2xs leading-relaxed text-ink-faint">
            Setiap sel grid dinilai terpisah untuk tiap jendela waktu di atas.
          </p>
        </Panel>
      </div>

      {config.versions.map((version) => (
        <Panel
          key={version.version}
          title={`Bobot — ${version.version}`}
          action={
            <span className="text-2xs uppercase tracking-wider text-ink-faint">
              {version.active ? "SEDANG DIPAKAI" : "tidak dipakai"} · {version.status}
            </span>
          }
        >
          {version.profiles.map((profile) => (
            <div key={profile.profile} className="mb-4 last:mb-0">
              <div className="mb-1.5 flex flex-wrap items-baseline gap-2">
                <span className="stat-label">{profile.profile}</span>
                <span className="text-2xs text-ink-faint">
                  berlaku untuk {profile.applies_to.join(", ") || "seluruh jenis"}
                </span>
                <span className="ml-auto font-mono text-2xs text-ink-muted">
                  jumlah bobot positif {profile.positive_weight_total}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-2xs uppercase tracking-wider text-ink-faint">
                      <th className="pb-1 font-normal">Faktor</th>
                      <th className="pb-1 text-right font-normal">Bobot</th>
                      <th className="pb-1 text-right font-normal">Tersimpan</th>
                      <th className="pb-1 font-normal">Dasar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.factors.map((factor) => (
                      <tr key={factor.factor} className="border-t border-base-800 align-top">
                        <td className="py-1.5 pr-3 font-mono text-xs text-ink">{factor.factor}</td>
                        <td
                          className={`py-1.5 pr-3 text-right font-mono ${
                            factor.sign === "negative" ? "text-risk-moderate" : "text-ink"
                          }`}
                        >
                          {factor.weight}
                        </td>
                        <td className="py-1.5 pr-3 text-right text-2xs text-ink-faint">
                          {factor.persisted ? "ya" : "tidak"}
                        </td>
                        <td className="py-1.5 text-2xs leading-relaxed text-ink-faint">
                          {factor.basis ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </Panel>
      ))}

      <Panel title="Cara Mengubah Konfigurasi">
        <p className="text-xs leading-relaxed text-ink-muted">
          Layar ini <strong>hanya membaca</strong>. Bobot dan ambang diubah dengan menyunting berkas
          di <span className="font-mono text-xs">config/risk/</span>, lalu membangun ulang image API
          — perubahan config <strong>tidak</strong> terbaca dengan sekadar memuat ulang container.
        </p>
        <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
          Ketiadaan formulir di sini bukan pekerjaan yang belum sempat. Setiap baris{" "}
          <span className="font-mono">risk_scores</span> menyimpan{" "}
          <span className="font-mono">weights_version</span>, dan versi yang masih dirujuk baris
          mana pun tidak boleh berubah isinya: menurunkannya akan membuat skor lama tampak terbit di
          bawah aturan yang tidak pernah berlaku saat itu, dan alasan terbitnya tidak lagi dapat
          ditelusuri. Cara yang benar untuk mengubah bobot adalah{" "}
          <strong>menambah versi baru</strong>.
        </p>
        <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
          Lihat{" "}
          <Link href="/skoring" className="underline hover:text-ink-muted">
            Penilaian Risiko
          </Link>{" "}
          untuk menjalankan penilaian dengan konfigurasi ini.
        </p>
      </Panel>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
      <div className="stat-label">{label}</div>
      <div className="mt-1 font-mono text-sm text-ink">{value}</div>
    </div>
  );
}
