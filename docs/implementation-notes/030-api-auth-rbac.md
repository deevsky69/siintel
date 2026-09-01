# TASK 030 + 050–053 — FONDASI API, AUTENTIKASI, OTORISASI, AUDIT

Tanggal: 2026-09-01
Status: **SELESAI — diverifikasi lewat HTTP nyata.**

Tahap B pada `docs/09`. Keempat task dikerjakan bersama karena memang tidak terpisah:
API domain tidak boleh lahir sebelum otorisasi dan audit hidup (`docs/08` PHASE 4).

---

## 1. YANG DIBUAT

```text
api/errors.py         format kesalahan baku + request_id
api/middleware.py     request id, log, header keamanan
api/pagination.py     amplop daftar baku
api/deps.py           session, pengguna aktif, require_permission, penyaring scope
api/routers/health.py health yang benar-benar memeriksa database
api/routers/auth.py   login, refresh, logout, me
security/passwords.py Argon2id + penanda akun terkunci
security/tokens.py    JWT access & refresh
services/permissions.py permission efektif dari database
services/audit.py     penulisan audit, termasuk DENIED
cli.py                set-password, list-users
```

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | **Password ditetapkan lewat CLI di server**, bukan lewat kode/seed | Kata sandi tidak pernah masuk repository maupun berkas seed, dan tidak muncul sebagai argumen perintah — dimasukkan lewat prompt tersembunyi |
| 2 | Akun hasil seed **terkunci** (`!`) sampai operator menetapkan kredensial | Sistem kepolisian tidak layak dimulai dengan kata sandi yang dapat ditebak |
| 3 | Verifikasi password **tetap dijalankan** meski akun tidak ada atau terkunci | Lamanya respons tidak boleh membedakan "akun tidak ada" dari "password salah" |
| 4 | Refresh token hanya pada cookie `httpOnly`, tidak pernah di body | Frontend tidak menyimpan secret (CLAUDE.md §23); ada test yang menjaganya |
| 5 | Refresh token **tidak dapat dipakai** sebagai access token | Jenis token diperiksa saat decode; ditukar berarti ditolak |
| 6 | `JWT_SECRET` wajib ≥32 byte; kosong di produksi = gagal start | HMAC-SHA256 dengan kunci pendek melemahkan tanda tangan (RFC 7518 §3.2). Peringatan pustaka JWT ditindak, bukan diabaikan |
| 7 | `JWT_SECRET` kosong saat pengembangan → secret sementara + peringatan | Tidak ada nilai default yang diam-diam terbawa ke produksi |
| 8 | Kesalahan validasi dijawab **400 VALIDATION_ERROR**, bukan 422 bawaan FastAPI | Kontrak `docs/05` §1 menyediakan 422 untuk pelanggaran aturan bisnis |
| 9 | Penolakan otorisasi **dicatat audit** sebelum kesalahan dilempar | Audit yang hanya memuat keberhasilan tidak dapat menilai kepatuhan RBAC |
| 10 | Scope terbatas tanpa penetapan wilayah/fungsi → **ditolak**, bukan menjadi akses penuh | Kegagalan harus menutup, bukan membuka |
| 11 | Data di luar cakupan dijawab **404**, bukan 403 | 403 membocorkan bahwa datanya ada di wilayah lain (`docs/05` §1) |
| 12 | Health memeriksa database dan melaporkan revisi migration | Health yang selalu hijau tidak berguna saat demo bermasalah |
| 13 | `docs`/`openapi.json` dimatikan pada `APP_ENV=production` | Mengurangi permukaan informasi pada demo publik |

---

## 3. VERIFIKASI LEWAT HTTP NYATA

```text
GET  /api/v1/health
  → {"status":"ok","database":{"status":"ok","migration":"0007"}}

POST /api/v1/auth/login  (password salah)
  → 401 {"error":{"code":"UNAUTHENTICATED","request_id":"a4356bf8…"}}

POST /api/v1/auth/login  (password benar, ditetapkan lewat CLI)
  → 200, access token pada body
  → set-cookie: predpol_refresh=…; HttpOnly; Max-Age=604800;
                Path=/api/v1/auth; SameSite=lax

GET  /api/v1/auth/me     (dengan token)
  → role Pimpinan, 21 permission, commander_decision:approve ADA,
    user:manage TIDAK ADA

GET  /api/v1/auth/me     (tanpa token) → 401

audit_logs → LOGIN|SUCCESS 1, LOGIN|DENIED 1
```

Penolakan masuk benar-benar meninggalkan jejak — itu yang membedakan audit dari log biasa.

Daftar pengguna setelah satu kredensial ditetapkan:

```text
USER-001  demo.pimpinan       Pimpinan        ACTIVE  aktif
USER-002  demo.commandcenter  Command Center  ACTIVE  terkunci
USER-003  demo.analyst        Analyst         ACTIVE  terkunci
…
```

```text
ruff + format (71 berkas) → bersih
mypy (63 berkas)          → no issues
pytest                    → 205 lulus
```

---

## 4. CARA MENETAPKAN PASSWORD

```bash
pnpm user:list                      # melihat akun dan status kredensialnya
pnpm user:password -- demo.pimpinan # prompt tersembunyi, dua kali konfirmasi
```

Panjang minimum 12 karakter adalah **pengaman teknis**, bukan kebijakan resmi;
kebijakan password organisasi masih menunggu penetapan (U-05).

---

## 5. BERIKUTNYA

`docs/09` Tahap B lanjutan: API baca (**031, 032, 036, 037, 038, 040**) lalu **TASK 070**
mengisi dashboard dengan data nyata.
