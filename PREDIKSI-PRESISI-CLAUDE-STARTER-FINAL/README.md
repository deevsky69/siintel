# PREDIKSI PRESISI — Claude Starter Package

## Tujuan
Paket ini menyiapkan fondasi dokumentasi agar Claude Code dapat membangun aplikasi
secara bertahap dan konsisten.

## Isi
- `CLAUDE.md` — aturan kerja Claude Code.
- `docs/01-master-technical-specification.md` — spesifikasi utama.
- `docs/02-data-dictionary.md` — template definisi data.
- `docs/03-role-permission-matrix.md` — draft RBAC.
- `docs/05-api-design.md` — draft kontrak API.
- `data/sample/` — tempat dataset sintetis.
- `design/` — tempat screenshot/logo/referensi UI.

## Cara mulai
1. Buat repository Git.
2. Extract/copy paket ini ke root repository.
3. Tambahkan referensi desain ke `design/`.
4. Isi data dictionary.
5. Review open items pada master specification.
6. Jalankan Claude Code dari root repository.
7. Minta Claude membaca `CLAUDE.md` dan `/docs` terlebih dahulu.
8. Jangan meminta Claude membangun seluruh aplikasi sekaligus.

## Prompt pertama yang disarankan

"Read CLAUDE.md and all relevant documents under /docs. Do not modify code yet.
Analyze the project requirements, architecture, dependencies, open decisions, and
risks. Then propose a phased implementation plan for the first vertical slice.
Wait for approval before coding."

## Data
Gunakan data sintetis/anonymized untuk development. Jangan memasukkan password,
API key, token, atau data pribadi/sensitif ke repository.

## Baseline arsitektur
Baca berurutan:
1. `docs/01-master-technical-specification.md`
2. `docs/02-data-dictionary.md`
3. `docs/03-role-permission-matrix.md`
4. `docs/04-erd.md`
5. `docs/05-api-design.md`
6. `docs/06-database-schema.md`
7. `docs/07-project-structure.md`

Dataset dummy berada di `data/sample/`.
