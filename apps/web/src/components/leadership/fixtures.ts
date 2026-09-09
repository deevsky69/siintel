import type { LeadershipBoard } from "@/lib/leadership";

/**
 * Contoh respons `GET /dashboard/leadership` untuk pengujian.
 *
 * Dipakai bersama oleh test panel dan test beranda. Disatukan supaya keduanya menguji
 * bentuk data yang sama: dua contoh terpisah akan menyimpang perlahan, dan test yang
 * lulus terhadap contoh usang berhenti menjaga apa pun.
 */
export const board: LeadershipBoard = {
  reference_time: "2025-12-31T21:00:00+07:00",
  demo_clock: true,
  reports_24h: {
    crime_incidents: 2,
    citizen_reports: 4,
    intelligence_reports: 1,
    total: 7,
    citizen_reports_without_location: 2,
    window_start: "2025-12-30T21:00:00+07:00",
    window_end: "2025-12-31T21:00:00+07:00",
    intelligence_date: "2025-12-31",
    basis: "Tiga jenis catatan dicacah terpisah.",
  },
  area_status: {
    assessment_date: "2025-12-31",
    mapping_status: "FINAL",
    basis:
      "Empat kelas dipetakan ke tiga nama status. Status pemetaan: FINAL — ditetapkan pemilik proyek.",
    mapping: [
      { status: "AMAN", label: "Aman", risk_classes: ["LOW"] },
      { status: "WASPADA", label: "Waspada", risk_classes: ["MODERATE"] },
      { status: "SIAGA", label: "Siaga", risk_classes: ["HIGH", "CRITICAL"] },
    ],
    tally: [
      { status: "AMAN", label: "Aman", areas: 0 },
      { status: "WASPADA", label: "Waspada", areas: 1 },
      { status: "SIAGA", label: "Siaga", areas: 2 },
    ],
    areas: [
      {
        kecamatan: "Pasar Minggu",
        risk_score: 88,
        risk_class: "CRITICAL",
        average_risk_score: 58,
        cell_count: 17,
        status: "SIAGA",
        label: "Siaga",
      },
      {
        kecamatan: "Cilandak",
        risk_score: 86,
        risk_class: "CRITICAL",
        average_risk_score: 50,
        cell_count: 16,
        status: "SIAGA",
        label: "Siaga",
      },
      {
        kecamatan: "Kebayoran Lama",
        risk_score: 69,
        risk_class: "MODERATE",
        average_risk_score: 49,
        cell_count: 12,
        status: "WASPADA",
        label: "Waspada",
      },
    ],
  },
  needs_attention: {
    basis: "Hanya hal yang masih menunggu manusia.",
    items: [
      {
        kind: "EARLY_WARNING",
        code: "WRN-0001",
        headline: "Peringatan CRITICAL — CURANMOR",
        kecamatan: "Tebet",
        detail: "Skor 93",
        why: "Belum diterima siapa pun.",
        since: "2025-12-30T11:00:00Z",
        rank: 93,
        href: "/peringatan?kode=WRN-0001",
      },
      {
        kind: "RECOMMENDATION",
        code: "REC-0009",
        headline: "Rekomendasi menunggu keputusan — SAMAPTA",
        kecamatan: "Tebet",
        detail: "Tingkatkan patroli",
        why: "Belum disetujui, dimodifikasi, maupun ditolak.",
        since: "2025-12-29T02:00:00Z",
        rank: 0,
        href: "/rekomendasi?kode=REC-0009",
      },
      {
        kind: "CITIZEN_REPORT",
        code: null,
        headline: "17 laporan masyarakat belum diverifikasi",
        kecamatan: null,
        detail: "Berstatus RECEIVED.",
        why: "Belum diverifikasi.",
        since: null,
        rank: 17,
        href: "/masyarakat?status=RECEIVED",
      },
    ],
  },
  priority_areas: [],
  top_report_areas: {
    days: 30,
    window_from: "2025-12-02",
    window_to: "2025-12-31",
    peak_reports: 11,
    unattributed_reports: 3,
    level_status: "PROPOSED",
    basis: "Tingkat pada daftar ini adalah peringkat volume laporan, bukan kelas risiko.",
    areas: [
      {
        kecamatan: "Cilandak",
        crime_incidents: 6,
        intelligence_reports: 4,
        citizen_reports: 1,
        reports: 11,
        level: "KRITIS",
        level_label: "Kritis",
        share_of_peak: 1,
      },
      {
        kecamatan: "Pancoran",
        crime_incidents: 5,
        intelligence_reports: 0,
        citizen_reports: 0,
        reports: 5,
        level: "SEDANG",
        level_label: "Sedang",
        share_of_peak: 0.455,
      },
    ],
  },
  prominent_issues: {
    days: 7,
    window_from: "2025-12-25",
    window_to: "2025-12-31",
    previous_from: "2025-12-18",
    previous_to: "2025-12-24",
    basis: "Perubahan disajikan sebagai selisih kejadian, bukan persen.",
    issues: [
      { threat_type: "CURANMOR", incidents: 5, previous_incidents: 1, change: 4 },
      { threat_type: "CURAS", incidents: 1, previous_incidents: 1, change: 0 },
    ],
  },
  policy: {
    basis: "Diturunkan dengan aturan dari agregat yang dihitung pada layar ini.",
    recommendations: [
      {
        action: "Tambah patroli pukul 20.00 s.d. 23.00 WIB di Pasar Minggu",
        function: "Samapta",
        basis: "Pasar Minggu berstatus Siaga dengan skor 88.",
        source: "RULE",
        href: "/wilayah/Pasar%20Minggu",
      },
    ],
  },
};

board.priority_areas = board.area_status.areas;
