import Link from "next/link";
import type { LeadershipBoard } from "@/lib/leadership";
import { AREA_STATUS_TONE, toneOf } from "@/lib/leadership";

/**
 * Sorotan beranda — satu judul, satu angka, satu baris keterangan.
 *
 * Bentuknya ditetapkan pemilik proyek, 3 September 2026: beranda memuat terlalu banyak
 * untuk dibaca sekali duduk, dan yang diminta adalah **grid dengan judul dan penjelasan
 * singkat**.
 *
 * Aturan yang dipakai di sini, dan sengaja dipegang ketat: **satu kartu menjawab satu
 * pertanyaan, dengan satu angka.** Rinciannya tidak dihapus — ia pindah ke layar yang
 * memang tugasnya menjelaskan, dan setiap kartu menautkannya. Kartu yang memuat tiga
 * angka dan dua paragraf berhenti menjadi sorotan dan berubah menjadi laporan kecil;
 * itulah keadaan sebelumnya.
 *
 * Angka besar dipasang tanpa satuan di dalamnya. Satuannya ada di judul dan di baris
 * keterangan, sehingga angka itu sendiri tetap dapat dibaca dari seberang ruangan —
 * layar ini dipakai saat paparan.
 */

function Card({
  title,
  value,
  tone,
  note,
  href,
  linkLabel,
}: {
  title: string;
  value: string;
  tone?: string;
  note: string;
  href: string;
  linkLabel: string;
}) {
  return (
    <section className="panel flex h-full flex-col">
      <div className="panel-body flex flex-1 flex-col">
        <h2 className="stat-label">{title}</h2>
        <p className={`mt-1.5 font-heading text-3xl font-bold leading-none ${tone ?? "text-ink"}`}>
          {value}
        </p>
        <p className="mt-2 flex-1 text-xs leading-relaxed text-ink-muted">{note}</p>
        <Link
          href={href}
          className="mt-2.5 text-2xs uppercase tracking-wider text-ink-faint transition-colors hover:text-accent"
        >
          {linkLabel} →
        </Link>
      </div>
    </section>
  );
}

export function Highlights({ board }: { board: LeadershipBoard }) {
  const reports = board.reports_24h;
  const dominant = board.area_status.tally.reduce(
    (best, row) => (row.areas > best.areas ? row : best),
    board.area_status.tally[0] ?? { status: null, label: "—", areas: 0 },
  );
  const attention = board.needs_attention.items;
  const decisions = attention.filter((item) => item.kind === "RECOMMENDATION").length;
  const warnings = attention.filter((item) => item.kind === "EARLY_WARNING").length;
  const top = board.priority_areas[0] ?? null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card
        title="Laporan Masuk"
        value={String(reports.total)}
        note={`24 jam terakhir — ${reports.crime_incidents} kejadian, ${reports.intelligence_reports} intelijen, ${reports.citizen_reports} dari warga.`}
        href="/informasi"
        linkLabel="Lihat semuanya"
      />

      <Card
        title="Status Wilayah"
        value={`${dominant.areas}/${board.area_status.areas.length}`}
        tone={toneOf(AREA_STATUS_TONE, dominant.status).split(" ")[0]}
        note={`Kecamatan berstatus ${dominant.label} pada penilaian ${board.area_status.assessment_date ?? "terakhir"}. Pemetaan status belum disetujui.`}
        href="/wilayah"
        linkLabel="Peringkat wilayah"
      />

      <Card
        title="Perlu Perhatian"
        value={String(attention.length)}
        tone={attention.length > 0 ? "text-risk-critical" : undefined}
        note={
          attention.length === 0
            ? "Tidak ada yang menunggu tindakan siapa pun."
            : `${warnings} peringatan belum diterima, ${decisions} menunggu keputusan Anda.`
        }
        href="/rekomendasi"
        linkLabel="Keputusan menunggu"
      />

      <Card
        title="Wilayah Prioritas"
        value={top ? String(top.risk_score) : "—"}
        tone={top ? toneOf(AREA_STATUS_TONE, top.status).split(" ")[0] : undefined}
        note={
          top
            ? `${top.kecamatan} — sel tertinggi, rata-rata wilayahnya ${top.average_risk_score}.`
            : "Belum ada penilaian risiko untuk kewenangan Anda."
        }
        href={top ? `/wilayah/${encodeURIComponent(top.kecamatan)}` : "/wilayah"}
        linkLabel="Rincian wilayah"
      />
    </div>
  );
}

/**
 * Yang menonjol — tiga hal yang berubah, bukan tiga hal yang ada.
 *
 * Bedanya menentukan. Daftar "sepuluh wilayah teratas" selalu terisi dan karenanya tidak
 * pernah memberi tahu apa pun yang baru; yang berguna dibaca setiap pagi adalah apa yang
 * **bergerak** sejak kemarin. Karena itu blok ini menyorot kenaikan terbesar, bukan angka
 * terbesar — dan mengaku kosong ketika memang tidak ada yang bergerak.
 */
export function Notables({ board }: { board: LeadershipBoard }) {
  const rising = board.prominent_issues.issues
    .filter((row) => row.change > 0)
    .sort((a, b) => b.change - a.change)[0];
  const action = board.policy.recommendations[0];
  const busiest = board.top_report_areas.areas[0];

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
      <Card
        title="Naik Paling Tajam"
        value={rising ? `+${rising.change}` : "—"}
        tone={rising ? "text-risk-critical" : undefined}
        note={
          rising
            ? `${rising.threat_type} — ${rising.incidents} kejadian pekan ini, sebelumnya ${rising.previous_incidents}.`
            : "Tidak ada jenis gangguan yang naik dibanding pekan lalu."
        }
        href="/analitik"
        linkLabel="Tren lengkap"
      />

      <Card
        title="Wilayah Terbanyak Lapor"
        value={busiest ? String(busiest.reports) : "—"}
        note={
          busiest
            ? `${busiest.kecamatan} — ${board.top_report_areas.days} hari terakhir. Volume laporan, bukan kerawanan.`
            : "Tidak ada laporan pada jendela ini."
        }
        href="/wilayah"
        linkLabel="Peringkat volume"
      />

      <Card
        title="Tindakan Disarankan"
        value={action ? action.function : "—"}
        note={
          action
            ? `${action.action}. Diturunkan aturan dari angka di layar ini, bukan keluaran model.`
            : "Tidak ada yang dapat diturunkan dari data pada jendela ini."
        }
        href="/rekomendasi"
        linkLabel="Seluruh rekomendasi"
      />
    </div>
  );
}
