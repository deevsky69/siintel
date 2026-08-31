# CLAUDE.md — PREDIKSI PRESISI

## 1. IDENTITAS PROYEK

Nama proyek: **PREDIKSI PRESISI**

Tema:
> Optimalisasi Deteksi Dini Kerawanan Kamtibmas melalui Predictive Policing Artificial Intelligence guna meningkatkan efektivitas pencegahan gangguan terpeliharanya Kamtibmas.

Dokumen ini adalah **aturan kerja utama untuk AI coding assistant (Claude)**.

Tujuan Claude bukan mengambil alih keputusan arsitektur secara sepihak, tetapi membantu mengimplementasikan spesifikasi proyek secara bertahap, konsisten, dapat diuji, dan dapat ditelusuri.

---

# 2. ATURAN PALING PENTING

Claude WAJIB:

1. Membaca seluruh dokumen di `docs/` yang relevan sebelum mengerjakan task.
2. Mengikuti ERD dan data dictionary sebagai sumber desain database.
3. Tidak mengarang requirement yang belum ditentukan.
4. Jika ada requirement yang ambigu atau konflik, **berhenti dan jelaskan konflik tersebut** sebelum membuat perubahan besar.
5. Mengutamakan perubahan kecil, terukur, dan dapat diuji.
6. Tidak membangun seluruh aplikasi sekaligus.
7. Setiap perubahan database harus menggunakan migration.
8. Setiap perubahan API harus memiliki dokumentasi dan test yang relevan.
9. Setiap fitur frontend harus dapat diuji secara lokal menggunakan dummy data.
10. Tidak memasukkan data rahasia atau data pribadi nyata ke repository.
11. Tidak melakukan destructive operation tanpa persetujuan eksplisit.
12. Tidak menghapus atau mengganti file existing hanya karena memiliki pendekatan yang berbeda tanpa menjelaskan alasannya.
13. Tidak mengganti framework/stack utama tanpa persetujuan.
14. Menampilkan file yang akan dibuat/diubah sebelum melakukan perubahan besar.
15. Setelah task selesai, berikan ringkasan:
   - file dibuat;
   - file diubah;
   - command untuk menjalankan/test;
   - hasil test;
   - masalah yang masih tersisa.

---

# 3. SUMBER KEBENARAN

Prioritas sumber requirement:

1. Requirement/proyek yang diberikan pengguna.
2. `docs/01-master-technical-specification.md`
3. `docs/02-data-dictionary.md`
4. `docs/03-role-permission-matrix.md`
5. `docs/04-erd.md`
6. `docs/05-api-design.md`
7. `docs/06-database-schema.md`
8. `docs/07-project-structure.md`
9. `docs/08-implementation-roadmap.md`
10. Source code yang sudah disepakati.

Jika source code bertentangan dengan spesifikasi, **jangan diam-diam mengubah spesifikasi**. Laporkan konflik dan usulkan solusi.

---

# 4. PRINSIP ARSITEKTUR

Arsitektur harus menjaga pemisahan:

```text
Web / Mobile
      ↓
    API
      ↓
Application / Business Logic
      ↓
 PostgreSQL + PostGIS
      ↓
 Analytics / ML Services
```

Frontend tidak mengakses database secara langsung.

Database menjadi sumber data terstruktur.

ML/predictive analytics tidak boleh bercampur dengan presentation layer.

---

# 5. PRINSIP PREDIKSI

Unit prediction adalah:

**wilayah + waktu**

bukan prediksi terhadap individu.

Prediction harus dapat menjelaskan minimal:

```text
WHAT
WHERE
WHEN
RISK
CONFIDENCE
WHY
```

`WHY` harus berisi faktor dominan yang dapat dipahami analyst/decision maker.

---

# 6. HUMAN-IN-THE-LOOP

Claude TIDAK BOLEH membangun workflow yang menjadikan AI sebagai pengambil keputusan operasional akhir.

Workflow utama:

```text
Data
 ↓
Analysis
 ↓
Prediction
 ↓
Risk Score
 ↓
Early Warning
 ↓
Recommendation
 ↓
Commander Decision
 ├── Approve
 ├── Modify
 └── Reject
 ↓
Operational Action
 ↓
Actual Result
 ↓
Evaluation
```

AI memberikan analisis/prediksi/rekomendasi.

Keputusan operasional tetap melalui manusia/pejabat berwenang.

---

# 7. DATA

Dataset pada:

```text
data/sample/
```

adalah data sintetis/dummy.

Dataset:

```text
data/raw/
```

diperlakukan sebagai data mentah dan berpotensi sensitif.

Jangan commit data resmi/sensitif ke Git.

Pipeline data:

```text
RAW
 ↓
VALIDATION
 ↓
MAPPING
 ↓
ANONYMIZATION
 ↓
GEO / GRID
 ↓
PROCESSED
 ↓
DATABASE
```

Jika format data resmi berbeda dengan canonical schema, buat ETL/mapping adapter.

**Jangan mengubah canonical schema hanya karena format file sumber berbeda.**

---

# 8. DATA PRIBADI

Untuk PoC, jangan menambahkan identitas korban, pelaku, saksi, atau data pribadi lain jika tidak diperlukan.

Jika suatu fitur membutuhkan data pribadi:

1. jelaskan tujuan;
2. tentukan field minimum;
3. batasi akses berdasarkan role;
4. pertimbangkan masking;
5. catat akses penting pada audit log;
6. jangan menggunakan data dummy yang menyerupai identitas nyata secara tidak perlu.

---

# 9. RISK SCORE

Risk score menggunakan rentang:

```text
0–100
```

Kelas yang dirancang:

```text
LOW
MODERATE
HIGH
CRITICAL
```

Namun Claude **DILARANG menganggap bobot dan threshold sebagai angka final** jika belum ditentukan oleh penelitian/model/SOP.

Jangan hard-code bobot prediksi tanpa requirement.

Simpan parameter yang memang dapat dikonfigurasi pada configuration layer.

---

# 10. EARLY WARNING

Level yang dirancang:

```text
LOW
WATCH
WARNING
CRITICAL
```

Threshold final tidak boleh diasumsikan.

Claude harus membuat mekanisme konfigurasi agar threshold dapat diubah tanpa mengubah banyak source code.

---

# 11. RECOMMENDATION

Recommendation adalah opsi tindakan.

Contoh fungsi:

```text
Samapta
Binmas
Intelkam
Reskrim
Lantas
```

Recommendation tidak boleh langsung menjalankan tindakan.

Harus melalui:

```text
Recommendation
      ↓
Commander Decision
      ↓
Operational Action
```

---

# 12. ROLE

Role utama:

```text
Pimpinan
Command Center
Analyst
Fungsi
Polsek
Administrator
```

Authorization harus berbasis role/permission.

Jangan hanya menyembunyikan tombol frontend.

Backend/API juga wajib memvalidasi permission.

---

# 13. AUDIT

Aktivitas penting harus dapat ditelusuri.

Contoh:

```text
login
view sensitive data
run prediction
publish warning
approve recommendation
modify recommendation
reject recommendation
create operational action
change configuration
import data
```

Audit log minimal menyimpan:

```text
timestamp
user
action
resource
resource_id
result
```

---

# 14. DATABASE

Baseline:

**PostgreSQL + PostGIS**

Canonical entity utama:

```text
locations
crime_incidents
intelligence_reports
patrol_activity
police_units

citizen_reports
public_alerts
community_feedback

risk_scores
predictions
early_warnings
recommendations

commander_decisions
operational_actions
prediction_actual

users
roles
permissions
role_permissions
audit_logs
```

Jangan membuat tabel baru hanya karena terasa nyaman.

Jika tabel baru memang diperlukan:

1. jelaskan alasannya;
2. update data dictionary;
3. update ERD;
4. buat migration;
5. buat test.

---

# 15. DATABASE MIGRATION

Semua perubahan schema:

```text
migration
    ↓
apply
    ↓
test
```

Jangan mengedit production database secara manual sebagai bagian normal workflow.

Migration harus reproducible.

---

# 16. API

API harus menjadi boundary utama antara frontend dan backend.

Setiap endpoint sensitif harus memiliki:

```text
Authentication
+
Authorization
+
Validation
+
Business Rule
+
Audit (jika relevan)
```

Input API harus divalidasi.

Jangan percaya data dari frontend.

---

# 17. FRONTEND

Frontend harus:

- menggunakan API;
- memiliki loading state;
- memiliki error state;
- memiliki empty state;
- memiliki responsive layout;
- tidak menaruh secret;
- tidak menaruh business rule sensitif yang seharusnya berada di backend.

Gunakan dummy data hanya sebagai fallback/development mechanism, bukan menggantikan API secara permanen.

---

# 18. GIS

Peta merupakan bagian penting sistem.

Data geospasial harus mendukung:

```text
Historical
Current Risk
Predictive Risk
```

Lokasi prediction menggunakan wilayah/grid, bukan identitas individu.

Jangan menampilkan detail sensitif ke user yang tidak memiliki permission.

---

# 19. MACHINE LEARNING

ML harus dapat direproduksi.

Setiap prediction menyimpan:

```text
model_version
prediction_date
forecast_horizon
location
threat_type
risk_score
confidence
dominant_factors
```

Jangan menyebut model sebagai "akurat" hanya karena menghasilkan angka.

Evaluation harus mengukur sekurang-kurangnya:

```text
Precision
Recall
False Positive
False Negative
```

dan metrik tambahan yang sesuai dengan penelitian.

---

# 20. EXPLAINABILITY

Jangan membuat AI explanation palsu.

Jika model menggunakan feature contribution, tampilkan kontribusi berdasarkan output model.

Jika menggunakan rule-based prototype, jelaskan bahwa faktor berasal dari rule.

Contoh:

```text
WHY

1. Recent incident trend meningkat
2. Historical incident density tinggi
3. Time window sesuai pola historis
4. Spatial concentration meningkat
```

Jangan mengklaim "AI menemukan pola" jika sistem sebenarnya hanya menggunakan data dummy/rule sederhana.

---

# 21. SECURITY

Minimum:

```text
Authentication
Authorization
Input Validation
Password Hashing
Secret Management
Audit Logging
Rate Limiting untuk endpoint yang relevan
Secure Headers
CORS yang terkontrol
```

Jangan commit:

```text
.env
password
API key
JWT secret
private key
credential
token
```

---

# 22. TESTING

Minimal:

```text
Unit Test
Integration Test
API Test
E2E Test
```

Untuk setiap feature penting:

```text
happy path
validation error
authorization error
empty state
failure state
```

---

# 23. CARA CLAUDE BEKERJA

Claude harus bekerja dengan pola:

```text
READ
 ↓
UNDERSTAND
 ↓
PLAN
 ↓
SHOW PLAN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
REPORT
```

Bukan:

```text
PROMPT
 ↓
CODING 500 FILE
 ↓
ERROR
```

---

# 24. FORMAT RESPONS CLAUDE SETIAP TASK

Setelah menyelesaikan task, gunakan format:

```text
## Task
...

## Plan
...

## Files Created
...

## Files Modified
...

## Database Changes
...

## API Changes
...

## Tests
...

## Commands
...

## Result
...

## Remaining Issues
...

## Next Recommended Task
...
```

---

# 25. JIKA TERJADI ERROR

Jangan langsung melakukan rewrite besar.

Urutan:

```text
Reproduce
 ↓
Read error
 ↓
Identify root cause
 ↓
Make smallest safe fix
 ↓
Run test
 ↓
Verify
```

Jika tidak yakin, jelaskan 2–3 kemungkinan dan minta keputusan pengguna jika perubahan berdampak besar.

---

# 26. JIKA REQUIREMENT BELUM ADA

Gunakan:

```text
NOT SPECIFIED
```

atau:

```text
PROPOSED — REQUIRES USER APPROVAL
```

Jangan mengubah:

```text
PROPOSED
```

menjadi:

```text
FINAL REQUIREMENT
```

tanpa persetujuan.

---

# 27. TAHAP IMPLEMENTASI

Ikuti roadmap di:

`docs/08-implementation-roadmap.md`

Jangan melompat langsung ke ML atau mobile sebelum fondasi yang dibutuhkan selesai.

Urutan baseline:

```text
0. Repository / specification audit
1. Project bootstrap
2. Database
3. Seed / dummy data
4. Backend API
5. Authentication + RBAC
6. Web shell
7. Dashboard
8. GIS
9. Analytics
10. Prediction prototype
11. Early Warning
12. Recommendation
13. Commander Approval
14. Operations
15. Evaluation
16. Hardening
17. Android / LAPOR PRESISI
```

---

# 28. DEFINITION OF DONE

Task dianggap selesai hanya jika:

- implementasi sesuai spesifikasi;
- tidak ada requirement penting yang diam-diam diasumsikan;
- test relevan dibuat/dijalankan;
- error utama tidak diabaikan;
- dokumentasi diperbarui jika desain berubah;
- migration dibuat jika schema berubah;
- tidak ada secret yang ditambahkan;
- Claude menjelaskan apa yang berubah.

---

# 29. ATURAN UNTUK PROJECT INI

**Jangan over-engineer.**

Ini proyek yang sedang dibangun dari 0.

Prioritaskan:

```text
Correctness
>
Traceability
>
Security
>
Testability
>
Maintainability
>
Feature count
```

Lebih baik 5 fitur benar-benar bekerja daripada 30 fitur setengah jadi.

