# TASK 121, 130 — REKOMENDASI & KEPUTUSAN KOMANDAN

Tanggal: 2026-09-01
Status: **SELESAI — diverifikasi lewat HTTP terhadap database nyata.**

Ini bagian yang paling menentukan bagi Taskap. Seluruh klaim bahwa PREDIKSI PRESISI
adalah alat bantu keputusan — bukan sistem yang memerintah sendiri — bertumpu pada
rantai berikut benar-benar ada di kode, bukan hanya di dokumen:

```
prediksi → peringatan → rekomendasi → KEPUTUSAN PEJABAT → tindakan operasional
```

Mata rantai keempat itulah yang dibangun di sini.

---

## 1. SATU ENDPOINT, BUKAN TIGA

```
POST /api/v1/recommendations/{code}/decisions
{"decision": "APPROVED" | "MODIFIED" | "REJECTED", "reason": "...", "modified_text": "..."}
```

Alternatifnya adalah tiga endpoint (`/approve`, `/modify`, `/reject`). Ditolak karena
keputusan adalah **entitas**, bukan tiga aksi berbeda (docs/05 §2.8): ia punya pelaku,
waktu, alasan, dan baris sendiri di `commander_decisions`. Dengan satu endpoint, aturan
transisi dan penulisan audit berada di satu tempat dan tidak bisa saling menyimpang.

| Permission | Peran yang memilikinya |
|---|---|
| `commander_decision:approve` | **Pimpinan saja** |
| `commander_decision:read` | Pimpinan (ALL), Command Center (ALL), Fungsi (OWN_FUNCTION), Polsek (OWN_JURISDICTION), Administrator (ALL) |

---

## 2. YANG DIJAGA, DAN MENGAPA

| # | Aturan | Alasan |
|---|---|---|
| 1 | Rekomendasi yang sudah diputus **tidak dapat diputus ulang** (409) | Memutus dua kali mengaburkan siapa yang memutuskan apa. Perubahan pendirian adalah keputusan baru atas rekomendasi baru, bukan penimpaan |
| 2 | `MODIFIED` wajib membawa isi baru (422) | Modifikasi tanpa isi tidak bermakna. Aturan yang sama juga dijaga CHECK `ck_commander_decisions_modified_needs_text` — API hanya menambahkan pesan yang dapat ditindaklanjuti |
| 3 | Usulan asli **tidak pernah ditimpa** | `recommendations.recommendation_text` tetap utuh; hasil modifikasi masuk ke `commander_decisions.modified_text`. Keduanya dikembalikan bersama dan ditampilkan berdampingan di layar (U-07) |
| 4 | `recommendations.status` hanyalah **cerminan** keputusan terakhir | Sumber kebenaran tetap baris keputusan. Status ditulis oleh proses yang sama yang menulis keputusan, tidak pernah sendirian (docs/02 §12) |
| 5 | Setiap keputusan menulis audit `APPROVE_/MODIFY_/REJECT_RECOMMENDATION` | Keputusan operasional tanpa jejak tidak dapat dipertanggungjawabkan |
| 6 | Data di luar cakupan dijawab **404, bukan 403** | 403 membocorkan bahwa datanya ada di wilayah lain (docs/05 §1) |

---

## 3. CELAH CAKUPAN YANG DITEMUKAN DAN DITUTUP

`GET /recommendations` sebelumnya tidak menyaring cakupan sama sekali. Rekomendasi
mewarisi wilayah dari prediksinya, dan tanpa `join` ke `locations` seorang pengguna
Polsek membaca seluruh rekomendasi Jakarta Selatan — termasuk lewat `total_items`.

Ini bukan kelalaian kosmetik: `config/rbac/permissions.yaml` **sudah** menyatakan
`recommendation:read` bagi Polsek ber-scope `OWN_JURISDICTION`. Kewenangan yang
dideklarasikan tetapi tidak ditegakkan lebih berbahaya daripada yang tidak
dideklarasikan, karena ia memberi rasa aman yang keliru.

Setelah diperbaiki, dengan data yang sama:

```text
Pimpinan  84 rekomendasi   64 keputusan
Polsek    13 rekomendasi    9 keputusan
```

---

## 4. LAYAR — MENAMPILKAN RANTAINYA, BUKAN MENYEMBUNYIKANNYA

`/rekomendasi` membagi daftar menjadi **Menunggu Keputusan** dan **Sudah Diputus**.
Yang menunggu diletakkan lebih dulu: itulah yang menuntut tindakan pejabat.

Tiga pilihan keputusan berdiri **sejajar** — bukan satu tombol "Setujui" besar dengan
"Tolak" tersembunyi di menu. Layar yang mendorong persetujuan sebagai jalan termudah
akan mengubah human-in-the-loop menjadi formalitas.

Pada rekomendasi yang sudah dimodifikasi, layar menampilkan **usulan sistem** dan
**rekomendasi setelah disesuaikan pejabat** berdampingan, beserta pertimbangannya.
Inilah bukti visual bahwa yang dijalankan di lapangan adalah penilaian manusia.

Tombol keputusan disembunyikan bagi peran tanpa kewenangan — **kenyamanan semata**.
Yang menolak tetap backend; akun Polsek yang memaksa mengirim permintaan dijawab 403
dan penolakannya masuk audit.

---

## 5. VERIFIKASI — LEWAT HTTP, DENGAN DATA NYATA

```text
rekomendasi menunggu keputusan   21   (REC-0006 RESKRIM)
Analyst mencoba memutuskan       403
MODIFIED tanpa isi baru          422  BUSINESS_RULE_VIOLATION
Pimpinan memodifikasi            201  DEC-0085 oleh demo.pimpinan
   usulan asli      "Pertimbangkan penguatan kegiatan preventif pada area…"
   hasil modifikasi "Patroli dimajukan ke pukul 17.00 dengan satu unit, bukan dua."
memutus ulang                    409  CONFLICT
status REC-0006                  MODIFIED   (teks asli tetap utuh)
```

Pada build produksi (Next.js port 3140 → API 8020) dengan sesi nyata:

```text
/rekomendasi                     200   panel keputusan tampil bagi Pimpinan
/rekomendasi?dipilih=REC-0006    200   DEC-0085, usulan asli + hasil modifikasi
akun demo.polsek                 200   tanpa satu pun kendali keputusan
```

---

## 6. SEBUAH TEST YANG DIPERBAIKI

`test_operational_seed_loads_expected_volumes` membandingkan `COUNT(*)` tabel
`commander_decisions` dengan angka tetap 63. Ia gagal begitu keputusan pertama dibuat
lewat API — padahal baris itu **sah**, dan justru bukti bahwa prototipe ini bekerja.

Test itu memeriksa **isi tabel**, sedangkan yang seharusnya dijaga adalah **perilaku
seed**. Diganti menjadi `test_operational_seed_loads_every_row_of_its_source`, yang
memastikan setiap baris berkas sumber termuat — tanpa melarang aplikasi menulis.

Ini pola kesalahan yang sama dengan `test_demo_accounts_cannot_be_used_to_log_in`
pada TASK 031 (lihat `031-read-apis.md` §4), dan pantas dicatat sebagai kecenderungan:
test yang mengunci keadaan basis data akan patah tepat ketika sistem mulai berguna.

---

## 7. YANG MASIH TERBUKA

| # | Hal | Menunggu |
|---|---|---|
| B-2 | Siapa yang berwenang menyetujui, dan apakah ada pendelegasian | **Keputusan pengguna** (P-1..P-7 pada docs/03) |
| 1 | Apakah keputusan boleh dianulir, dan oleh siapa | SOP. Saat ini: tidak bisa (409), pilihan paling aman |
| 2 | Tindakan operasional belum dapat dibuat dari layar | TASK berikutnya. Invariannya sudah dijaga trigger database sejak TASK 014 |
| 3 | Nomor keputusan `DEC-0085` diturunkan dari kode terbesar | Cukup untuk demo; bila kelak ada penulisan serentak, perlu sequence database |
