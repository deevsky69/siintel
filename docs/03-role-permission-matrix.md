# ROLE–PERMISSION MATRIX — PREDIKSI PRESISI

> Status: **Katalog permission = `TECHNICAL DECISION`. Pemberian permission per role = `PROPOSED` (butuh persetujuan pemilik proyek).**
> Dasar: CLAUDE.md §15 (authorization ditegakkan di backend), docs/01 §4.

---

## 1. ROLE

| Level | Role | Ruang lingkup |
|---|---|---|
| 1 | Pimpinan | Dashboard strategis, prediksi, rekomendasi, persetujuan |
| 4 | Fungsi | Sesuai fungsi yang diberi kewenangan (Intelkam/Reskrim/Samapta/Binmas/Lantas) |
| 5 | Polsek | Data dan situasi di wilayah hukumnya |
| 6 | Administrator | Konfigurasi teknis, manajemen user/sistem, monitoring, analitik |

> **Penggabungan peran — keputusan pemilik proyek, 1 September 2026, ditegaskan kembali
> 9 September 2026.** Level 2 (*Command Center*) dan level 3 (*Analyst*) **dihapus**;
> keduanya menjadi Administrator penuh. Nomor level 2 dan 3 sengaja dibiarkan kosong
> alih-alih dinomori ulang, supaya rujukan lama pada dokumen dan catatan implementasi
> tidak berpindah arti.
>
> Administrator karenanya memegang 40 dari 43 permission. Dua yang sengaja berada di
> luar jangkauannya milik Pimpinan: `commander_decision:approve` (yang mengusulkan tidak
> boleh menjadi yang memutuskan) dan `evaluation:run` (yang menghasilkan angka tidak
> boleh menilai ketepatannya sendiri).

---

## 2. MODEL PERMISSION

`TECHNICAL DECISION` — permission dinyatakan sebagai pasangan **`resource:action`**, dan pemberiannya ke role membawa **`scope`**:

| Scope | Arti |
|---|---|
| `ALL` | Seluruh wilayah/fungsi |
| `OWN_JURISDICTION` | Hanya data yang `location.polsek` = `users.polsek` |
| `OWN_FUNCTION` | Hanya data yang `function` = `users.function` |

`scope` menggantikan simbol `L` (limited) pada draf lama, yang sebelumnya tidak punya penopang di model data.
Penegakan `scope` terjadi **di backend** (query filter), bukan di frontend.

> Tanpa `users.polsek` dan `users.function` (ditambahkan pada docs/02 §17), `scope` tidak dapat ditegakkan.

### Katalog permission

| Resource | Action | Keterangan |
|---|---|---|
| `dashboard` | `read` | Ringkasan eksekutif |
| `location` | `read`, `write` | Master wilayah/grid |
| `crime` | `read`, `write`, `export` | Data kejadian |
| `intelligence` | `read`, `write` | Laporan intelijen |
| `patrol` | `read`, `write` | Kegiatan patroli |
| `police_unit` | `read`, `write` | Satuan/unit |
| `map` | `read` | Layer peta |
| `analytics` | `read`, `export` | Tren, pola waktu/ruang, Crime Pattern DNA |
| `risk_score` | `read`, `run` | Layer risiko berjalan |
| `prediction` | `read`, `run`, `publish` | Prediksi; `publish` mengubah `DRAFT`→`PUBLISHED` |
| `warning` | `read`, `acknowledge`, `resolve` | Early warning |
| `public_alert` | `read`, `publish` | Alert untuk publik |
| `recommendation` | `read`, `write` | Opsi tindakan |
| `commander_decision` | `read`, `approve` | Approve/Modify/Reject |
| `operation` | `read`, `write` | Operational action & assignment |
| `citizen_report` | `read`, `write` | Laporan masyarakat |
| `community_feedback` | `read` | Umpan balik masyarakat |
| `evaluation` | `read`, `run` | Prediction vs actual, metrik model |
| `user` | `read`, `manage` | Manajemen pengguna |
| `role` | `read`, `manage` | Role & permission |
| `audit` | `read` | Audit trail — **tidak ada `write`/`delete`** |
| `config` | `read`, `manage` | Bobot risiko, threshold, taksonomi |

**Catatan `audit` (`TECHNICAL DECISION`).** Draf lama memberi Administrator hak `RW` atas audit logs. Hak tulis/hapus atas audit dihapus dari katalog: audit bersifat *append-only* dan ditulis oleh sistem, bukan oleh pengguna. Memberi peran mana pun kemampuan mengubah audit meniadakan nilai audit sebagai bukti governance (CLAUDE.md §29).

**Catatan `config`.** Perubahan konfigurasi (bobot/threshold) wajib tercatat di audit (`CHANGE_CONFIGURATION`) sesuai CLAUDE.md §29.

---

## 3. MATRIKS ROLE → PERMISSION (`PROPOSED`)

**Tabel di bawah dibangkitkan dari `config/rbac/permissions.yaml`** — sumber yang
benar-benar dipakai seeder RBAC dan ditegakkan backend. Jangan menyuntingnya dengan
tangan; ubah konfigurasinya lalu jalankan:

```bash
python3 scripts/matriks-rbac.py --tulis
```

Alasannya konkret: sampai 9 September 2026 tabel ini ditulis tangan, dan ia sudah
menyimpang jauh. Ia masih memuat kolom Command Center dan Analyst — dua peran yang
dihapus 1 September 2026 — dan memberi Administrator sekadar `read` pada hampir seluruh
resource, padahal peran itu sesungguhnya memegang 40 dari 43 permission. Dokumen yang
bertentangan dengan konfigurasi yang dijalankan lebih berbahaya daripada dokumen yang
tidak ada, karena ia tetap dibaca sebagai kebenaran.

Format sel: `action(scope)`. Tanda `—` berarti peran itu tidak memegang satu pun
permission atas resource tersebut.

<!-- matriks:mulai -->

| Resource | Pimpinan | Fungsi | Polsek | Administrator |
|---|---|---|---|---|
| dashboard | read(ALL) | read(ALL) | read(OWN_JURISDICTION) | read(ALL) |
| location | read(ALL) | read(ALL) | read(ALL) | read, write(ALL) |
| crime | read(ALL) | read, write(ALL) | read, write(OWN_JURISDICTION) | read, write, export(ALL) |
| intelligence | read(ALL) | — | read(OWN_JURISDICTION) | read, write(ALL) |
| patrol | read(ALL) | read, write(OWN_FUNCTION) | read, write(OWN_JURISDICTION) | read, write(ALL) |
| police_unit | read(ALL) | read(OWN_FUNCTION) | read(OWN_JURISDICTION) | read, write(ALL) |
| map | read(ALL) | read(ALL) | read(OWN_JURISDICTION) | read(ALL) |
| analytics | read(ALL) | read(ALL) | read(OWN_JURISDICTION) | read, export(ALL) |
| risk_score | read(ALL) | read(ALL) | read(OWN_JURISDICTION) | read, run(ALL) |
| prediction | read(ALL) | read(ALL) | read(OWN_JURISDICTION) | read, run, publish(ALL) |
| warning | read(ALL) | read(ALL) | read, acknowledge(OWN_JURISDICTION) | read, acknowledge, resolve(ALL) |
| public_alert | read, publish(ALL) | read(ALL) | read(OWN_JURISDICTION) | read(ALL) |
| recommendation | read(ALL) | read(OWN_FUNCTION) | read(OWN_JURISDICTION) | read, write(ALL) |
| commander_decision | read, approve(ALL) | read(OWN_FUNCTION) | read(OWN_JURISDICTION) | read(ALL) |
| operation | read(ALL) | read(OWN_FUNCTION) | read(OWN_JURISDICTION) | read, write(ALL) |
| citizen_report | read(ALL) | — | read, write(OWN_JURISDICTION) | read, write(ALL) |
| community_feedback | read(ALL) | — | read(OWN_JURISDICTION) | read(ALL) |
| evaluation | read, run(ALL) | read(ALL) | read(OWN_JURISDICTION) | read(ALL) |
| user | — | — | — | read, manage(ALL) |
| role | — | — | — | read, manage(ALL) |
| audit | read(ALL) | — | — | read(ALL) |
| config | read(ALL) | — | — | read, manage(ALL) |

Jumlah permission per peran: Pimpinan 23, Fungsi 17, Polsek 22, Administrator 40.

<!-- matriks:selesai -->

Statusnya tetap `PROPOSED`: yang dibangkitkan adalah **isi tabelnya**, bukan
persetujuan atasnya. Pemberian permission per peran menunggu jawaban P-1…P-7 di §4.

---

## 4. YANG MASIH MENUNGGU KEPUTUSAN PENGGUNA

Butir berikut adalah **keputusan kewenangan organisasi**, bukan keputusan teknis (`REQUIRES HUMAN / POLICY APPROVAL`, CLAUDE.md §2C/§2D):

| # | Pertanyaan | Terkait |
|---|---|---|
| P-1 | Siapa yang berwenang menyetujui rekomendasi — hanya Pimpinan, atau Administrator juga untuk prioritas rendah? | `commander_decision:approve` |
| P-2 | **Separuh dijawab 9 September 2026:** kewenangan menerbitkan alert publik ada pada **Pimpinan**. Yang masih terbuka: mulai severity berapa sebuah peringatan pantas diumumkan. | `public_alert:publish` (U-10) |
| P-3 | Administrator kini boleh mem-*publish* prediksi tanpa persetujuan siapa pun. Apakah itu dikehendaki, atau publikasi perlu ditahan Pimpinan? | `prediction:publish` |
| P-4 | Definisi jurisdiksi Polsek: apakah dibatasi `location.polsek`, atau ada pengecualian lintas wilayah? | `OWN_JURISDICTION` (U-06) |
| P-5 | Apakah role Fungsi dibatasi per fungsi (Intelkam/Reskrim/…) atau melihat seluruh fungsi? | `OWN_FUNCTION` (U-06) |
| P-6 | Fungsi dan Polsek belum memegang `audit:read` sama sekali, karena `audit_logs` tidak punya kolom lokasi sehingga OWN_JURISDICTION mustahil ditegakkan. Apakah keduanya tetap tanpa akses audit? | `audit:read` |
| P-7 | Siapa yang boleh mengubah bobot risiko/threshold pada produksi? Saat ini Administrator, bersama seluruh `config:manage`. | `config:manage` |

Sampai P-1…P-7 dijawab, matriks §3 berstatus `PROPOSED` dan hanya dipakai sebagai baseline pengembangan.

---

## 5. IMPLIKASI IMPLEMENTASI

1. Setiap endpoint pada `docs/05` mencantumkan permission yang diperlukan; middleware memeriksanya sebelum handler dijalankan (TASK 052).
2. Test wajib mencakup tiga kasus per endpoint sensitif: **allowed**, **denied**, **unauthenticated** (CLAUDE.md §30).
3. Penolakan otorisasi dicatat ke audit dengan `result = DENIED` (docs/02 §20).
4. Seed `permissions`/`role_permissions` mengikuti katalog §2 dan matriks §3 — dataset dummy lama (12 permission, tanpa `scope`) tidak lagi mencerminkan model ini dan diperbarui pada TASK 020 (lihat docs/08).
