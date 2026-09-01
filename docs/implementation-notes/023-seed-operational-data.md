# TASK 023 — SEED OPERATIONAL DATA

Tanggal: 2026-09-01
Status: **SELESAI — dimuat ke PostgreSQL 17.5 dan diverifikasi.**

| Tabel | Jumlah |
|---|---:|
| `commander_decisions` | 63 |
| `operational_actions` | 52 |
| `prediction_actual` | 241 |

---

## 1. TIGA TEMUAN AUDIT DITUTUP

| Temuan | Sebelum | Sesudah |
|---|---|---|
| **A-1** `decision_by` menunjuk pengguna yang tidak ada | 63 dari 63 baris | **0** — seluruhnya menunjuk `USER-001` (Pimpinan) |
| **A-8** tindakan operasional | 3 tindakan untuk 52 keputusan menyetujui, **2 di antaranya lahir dari keputusan `Rejected`** | 52 tindakan, **0** dari keputusan `Rejected` |
| **A-7** evaluasi | 29 evaluasi atas prediksi `Draft`; **0 false negative** | hanya prediksi terbit; **90 false negative**, seluruhnya menunjuk kejadian nyata |

### Temuan tambahan yang muncul saat pengerjaan

Dataset semula memuat `ACT-0001` dan `ACT-0002` yang merujuk keputusan **`Rejected`**.
Artinya, pada data yang selama ini dipakai, **tindakan operasional pernah dibuat tanpa
persetujuan** — persis pelanggaran yang membuat seluruh rantai human-in-the-loop kehilangan
maknanya.

Trigger `trg_operational_actions_require_approved_decision` (TASK 014) akan **menolak** baris
seperti itu. Jadi seandainya data lama dimuat apa adanya, PostgreSQL yang menghentikannya —
bukan sekadar tidak lolos tinjauan manusia. Ada integration test yang membuktikannya.

---

## 2. RECALL AKHIRNYA DAPAT DIHITUNG

Ini alasan utama task ini penting bagi Taskap. Sebelumnya `prediction_actual` hanya memuat
`Hit` dan `False Positive`, sehingga **recall mustahil dihitung** dan klaim evaluasi model tidak
memiliki dasar (CLAUDE.md §26).

Hasil pada database:

```text
HIT              60
FALSE_POSITIVE   91
FALSE_NEGATIVE   90

precision = 60 / (60 + 91) = 0,397
recall    = 60 / (60 + 90) = 0,400
```

### Cakupan evaluasi (PROPOSED)

False negative dibangkitkan dari kejadian nyata pada periode prediksi (1 Okt – 31 Des 2025)
yang berada di sel **tanpa prediksi terbit**. Cakupannya dibatasi pada tiga jenis ancaman yang
memang diprediksi sistem — `CURANMOR`, `CURAT`, `CURAS`.

`TAWURAN` dan `KEJAHATAN_JALANAN` **tidak** dihitung sebagai false negative: memasukkannya
berarti menghukum model atas ancaman yang tidak pernah masuk cakupannya. Aturan cakupan ini
berstatus `PROPOSED` sampai U-03 (definisi target prediksi dan aturan pencocokan) dijawab,
dan angka precision/recall di atas harus disajikan dengan penanda itu.

---

## 3. YANG MASIH PERLU KEPUTUSAN — KETERTELUSURAN `HIT`

Satu ketidakkonsistenan ditemukan tetapi **sengaja tidak diperbaiki** di sini karena berada di
luar acceptance TASK 023 dan menyangkut keputusan yang bukan milik saya:

Baris `HIT` menyatakan sebuah kejadian terjadi pada sel yang diprediksi, tetapi **tidak ada satu
pun kejadian pada `crime_incidents` yang jatuh di sel berprediksi**. Artinya 60 baris `HIT`
tidak dapat ditelusuri ke kejadian nyata mana pun; nilainya asersi dataset, bukan hasil
pencocokan.

Konsekuensinya: angka **recall** berpijak pada kejadian nyata, sedangkan angka **precision**
belum. Tiga pilihan:

| Opsi | Konsekuensi |
|---|---|
| **A.** Turunkan `HIT`/`FALSE_POSITIVE` dari data kejadian | Paling jujur, tetapi dengan data sekarang seluruh 151 prediksi menjadi `FALSE_POSITIVE` — precision 0, demo kehilangan makna |
| **B.** Pindahkan sebagian prediksi ke sel yang benar-benar ada kejadiannya | Precision dan recall keduanya berpijak pada kejadian nyata; berarti membangkitkan ulang `predictions` sekali lagi |
| **C.** Biarkan seperti sekarang | Recall sahih, precision berstatus asersi dataset — harus dinyatakan terbuka saat dipresentasikan |

Rekomendasi saya: **B**, dikerjakan bersama TASK 100–104 ketika prediksi dihasilkan model,
bukan diambil dari dataset. Sampai saat itu, opsi C berlaku dengan penanda terbuka.

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
regenerate + regenerate_operational (dua kali) → berkas identik (deterministik)
pnpm seed:operational                          → 63 + 52 + 241 baris
dijalankan ulang                               → +0 (idempoten)

Di database:
  keputusan APPROVED 33 → 33 tindakan
  keputusan MODIFIED 19 → 19 tindakan
  keputusan REJECTED 11 →  0 tindakan
  false negative tanpa kejadian → 0
  precision 0,397   recall 0,400

ruff check + format (55 berkas) → bersih
mypy (47 berkas)                → no issues
pytest tanpa DATABASE_URL       → 134 lulus, 55 dilewati
pytest dengan DATABASE_URL      → 189 lulus
```

Dua bug ditemukan dan diperbaiki saat pengerjaan:

1. Penomoran evaluasi baru dihitung dari **jumlah** baris, padahal kode lama memiliki celah
   setelah 29 baris dibuang — akibatnya menabrak kode yang sudah terpakai (`EVA-00152`).
   Diganti memakai nomor tertinggi yang sudah ada.
2. `modified_text` belum ada di berkas sumber, padahal CHECK database mewajibkannya untuk
   keputusan `MODIFIED` (U-07). Kolomnya ditambahkan saat pembangkitan ulang.

---

## 5. TASK BERIKUTNYA

**TASK 024 — Seed Public & Administration Data**: `citizen_reports`, `public_alerts`,
`community_feedback`, `audit_logs`.

Dua temuan audit menunggu:

| Temuan | Acceptance |
|---|---|
| Pasangan `action`/`resource_type` pada audit acak dan tidak bermakna | A-9 |
| ±190 baris audit mencatat `SUCCESS` untuk aksi yang role-nya tidak berwenang, dan tidak ada satu pun `DENIED` | A-9, A-10 |

Audit yang mencatat keberhasilan atas aksi tanpa kewenangan adalah kebalikan dari fungsi audit
itu sendiri — dan itulah bukti utama yang biasanya diminta saat menilai kepatuhan RBAC.
