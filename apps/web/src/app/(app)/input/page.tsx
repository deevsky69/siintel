import Link from "next/link";
import { Panel } from "@/components/panel";
import { areaOf, getCitizenReports, labelOf, REPORT_STATUS_LABELS } from "@/lib/community";
import {
  byPolsek,
  getEntryOptions,
  getLocations,
  locationLabel,
  referenceDate,
} from "@/lib/data-entry";
import { getProfile } from "@/lib/decisions";
import { CrimeForm } from "./crime-form";
import { IntelligenceForm } from "./intelligence-form";
import type { LocationGroup, TriageReport } from "./options";
import { TriageForm } from "./triage-form";

export const dynamic = "force-dynamic";

/**
 * Input Data (TASK 132) — pintu masuk data ke sistem.
 *
 * Sebelum layar ini, jawaban jujur atas pertanyaan "bagaimana data masuk ke sistem?"
 * adalah: lewat proses seed. Katalog RBAC memuat 43 permission, tetapi aksi tulis yang
 * benar-benar ada baru lima. Layar ini menambah tiga yang paling mendasar — kejadian
 * kriminal, laporan intelijen, dan triase laporan masyarakat.
 *
 * Tab disimpan di URL (`?formulir=`), bukan state klien, agar halaman tetap server
 * component dan tautannya dapat dibagikan saat paparan — pola yang sama dengan
 * `/operasi` dan `/rekomendasi`.
 *
 * Formulir disembunyikan bagi peran tanpa kewenangan. Itu **hanya kenyamanan**: yang
 * menolak sesungguhnya adalah backend, dan penolakannya ikut tercatat di audit
 * (CLAUDE.md §21, §29).
 */

type TabKey = "kejadian" | "intelijen" | "triase";

const TABS: { key: TabKey; label: string; permission: string; noun: string }[] = [
  {
    key: "kejadian",
    label: "Kejadian Kriminal",
    permission: "crime:write",
    noun: "kejadian kriminal",
  },
  {
    key: "intelijen",
    label: "Laporan Intelijen",
    permission: "intelligence:write",
    noun: "laporan intelijen",
  },
  {
    key: "triase",
    label: "Triase Laporan Masyarakat",
    permission: "citizen_report:write",
    noun: "perubahan status laporan masyarakat",
  },
];

const TAB_ACTIVE = "border-accent/60 bg-accent/10 text-accent";
const TAB_IDLE = "border-base-800 text-ink-muted hover:border-accent/40 hover:text-accent-soft";

function tabOf(value: string | string[] | undefined): TabKey {
  const candidate = typeof value === "string" ? value : "";
  const found = TABS.find((tab) => tab.key === candidate);
  return found ? found.key : "kejadian";
}

/**
 * Keadaan "tidak berwenang" — salah satu dari lima keadaan wajib tiap halaman
 * (CLAUDE.md §23). Ditulis sebagai kalimat, bukan sebagai formulir yang mati rasa.
 */
function Unauthorized({ noun, extra }: { noun: string; extra?: string }) {
  return (
    <div className="text-xs leading-relaxed text-ink-muted">
      <p>
        Akun Anda tidak memiliki kewenangan mencatat {noun}, sehingga formulirnya tidak ditampilkan.
        Menyembunyikannya hanya kenyamanan — backend tetap menolak permintaan yang dikirim tanpa
        kewenangan, dan percobaannya tercatat di audit trail.
      </p>
      {extra ? <p className="mt-2">{extra}</p> : null}
    </div>
  );
}

/**
 * Keterangan yang harus ikut terbaca pada tab intelijen.
 *
 * Ini fakta konfigurasi per 1 September 2026, bukan tebakan: `intelligence:write` ada di
 * katalog `config/rbac/permissions.yaml` tetapi tidak diberikan kepada satu peran pun.
 * Pemberiannya kepada peran Fungsi ditahan karena `intelligence_reports` tidak punya
 * kolom fungsi, sehingga cakupan `OWN_FUNCTION` mustahil ditegakkan — dan menaikkannya
 * menjadi `ALL` adalah pelebaran kewenangan, keputusan pemilik proyek.
 */
const INTELLIGENCE_NOTE =
  "Perlu diketahui: per konfigurasi RBAC 1 September 2026, `intelligence:write` ada di katalog permission tetapi belum diberikan kepada peran mana pun — termasuk Administrator. Endpoint-nya sudah ada dan diuji; yang kurang adalah keputusan siapa yang berwenang menulis laporan intelijen, dan itu keputusan pemilik proyek.";

export default async function DataEntryPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const active = tabOf(params.formulir);

  // Profil dibaca lebih dulu: daftar laporan masyarakat hanya boleh diminta bila perannya
  // memang berwenang membacanya. Memintanya tanpa syarat akan membuat seluruh halaman
  // gagal bagi peran Fungsi, yang tidak memegang `citizen_report:read`.
  const profile = await getProfile();
  const allows = (permission: string) => profile.permissions.includes(permission);

  const [options, locations] = await Promise.all([getEntryOptions(), getLocations()]);
  const reports = allows("citizen_report:read") ? await getCitizenReports({ pageSize: 200 }) : null;

  const locationGroups: LocationGroup[] = byPolsek(locations.data).map((group) => ({
    polsek: group.polsek,
    options: group.rows.map((row) => ({ value: row.code, label: locationLabel(row) })),
  }));

  const triageReports: TriageReport[] = (reports?.data ?? []).map((row) => ({
    code: row.code,
    label: `${row.category} · ${areaOf(row)}`,
    status: row.status,
    statusLabel: labelOf(REPORT_STATUS_LABELS, row.status),
  }));

  const maxDate = referenceDate(options.reference_time);
  const current = TABS.find((tab) => tab.key === active) ?? TABS[0];

  return (
    <Panel title={`Input Data — ${current.label}`}>
      <nav aria-label="Formulir pemasukan data" className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <Link
            key={tab.key}
            href={`/input?formulir=${tab.key}`}
            aria-current={tab.key === active ? "page" : undefined}
            className={`rounded border px-3 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider transition ${
              tab.key === active ? TAB_ACTIVE : TAB_IDLE
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      <p className="mt-3 border-b border-base-800 pb-3 text-2xs leading-relaxed text-ink-muted">
        Nilai taksonomi mengikuti <code>config/taxonomy/mappings.yaml</code> versi{" "}
        <span className="font-mono">{options.taxonomy_version}</span> dan berstatus PROPOSED (U-16).{" "}
        {options.demo_clock
          ? `Waktu acuan aplikasi beku pada ${maxDate}; tanggal setelah itu ditolak backend.`
          : "Aplikasi memakai waktu sebenarnya."}
      </p>

      <div className="mt-4">
        {active === "kejadian" ? (
          allows("crime:write") ? (
            <CrimeForm
              incidentTypes={options.incident_type}
              statuses={options.crime_status}
              locations={locationGroups}
              locationTypes={options.suggestions.location_type ?? []}
              modusOptions={options.suggestions.modus ?? []}
              targetTypes={options.suggestions.target_type ?? []}
              maxDate={maxDate}
              demoClock={options.demo_clock}
            />
          ) : (
            <Unauthorized noun={current.noun} />
          )
        ) : null}

        {active === "intelijen" ? (
          allows("intelligence:write") ? (
            <IntelligenceForm
              statuses={options.intelligence_status}
              impacts={options.impact}
              locations={locationGroups}
              categories={options.suggestions.intelligence_category ?? []}
              reliabilities={options.suggestions.reliability ?? []}
              maxDate={maxDate}
              demoClock={options.demo_clock}
            />
          ) : (
            <Unauthorized noun={current.noun} extra={INTELLIGENCE_NOTE} />
          )
        ) : null}

        {active === "triase" ? (
          allows("citizen_report:write") ? (
            <TriageForm
              reports={triageReports}
              statuses={options.citizen_report_status}
              verificationBasis={options.verification_basis}
              transitionBasis={options.transition_basis}
            />
          ) : (
            <Unauthorized noun={current.noun} />
          )
        ) : null}
      </div>
    </Panel>
  );
}
