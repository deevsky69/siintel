# PANDUAN DEPLOYMENT — PREDIKSI PRESISI

> Status: **BERLAKU** untuk Tahap E (`docs/09-rencana-menuju-paparan.md`) — TASK D-1 dan D-2.
> Pembaca yang dituju: pemilik proyek, bukan penghafal perintah Docker.
> Seluruh perintah ditulis lengkap dan boleh disalin apa adanya.

---

## 0. GAMBARAN SINGKAT — APA YANG SEBENARNYA DIPASANG

Tiga container aplikasi berjalan berdampingan, di belakang satu reverse proxy:

```text
                     Internet
                        │
                     HTTPS (443)
                        │
                        ▼
        ┌───────────────────────────────┐
        │  reverse proxy                │  ← satu-satunya yang terbuka ke internet
        │  (Traefik-nya Coolify)        │
        └───────────────┬───────────────┘
                        │  jaringan internal
                        ▼
        ┌───────────────────────────────┐
        │  web     — Next.js            │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  api     — FastAPI            │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  db      — PostgreSQL+PostGIS │
        └───────────────────────────────┘
```

Yang penting dipahami: **hanya reverse proxy yang dapat dihubungi dari internet.**
Database dan API tidak memiliki pintu ke luar sama sekali. Ini mungkin karena halaman web
memanggil API dari sisi server Next.js, bukan dari peramban pengunjung
(`apps/web/src/lib/api.ts`). Akibatnya token tidak pernah menyentuh peramban, dan tidak ada
alamat backend yang perlu dijaga.

Berkas yang mengatur semuanya:

| Berkas | Isi |
|---|---|
| `infra/docker/docker-compose.prod.yml` | susunan `db`, `api`, `web` — **tanpa** pintu masuk |
| `infra/docker/docker-compose.coolify.yml` | **JALUR A** — pintu masuk lewat Traefik-nya Coolify |
| `infra/docker/docker-compose.caddy.yml` | **JALUR B** — pintu masuk dengan Caddy sendiri |
| `infra/docker/Caddyfile` | aturan HTTPS dan header keamanan untuk JALUR B |
| `apps/api/Dockerfile` | cara image API dibangun |
| `apps/web/Dockerfile` | cara image web dibangun |
| `.env.production` | **seluruh nilai rahasia — tidak di-commit** |

---

## 1. MEMILIH JALUR — BACA INI LEBIH DAHULU

Berkas dasar `docker-compose.prod.yml` sengaja **tidak** memuat reverse proxy dan tidak
membuka satu port pun ke host. Pintu masuknya dipilih dengan menambahkan satu berkas.

### JALUR A — **INILAH YANG DIPAKAI SERVER DEMO**

Server ini **sudah menjalankan Coolify**, dan proxy bawaannya (`coolify-proxy`,
Traefik v3.6) sudah memegang port 80, 443, dan 8080. Fakta yang diperiksa langsung di
server, bukan dugaan:

```text
coolify-proxy   traefik:v3.6   0.0.0.0:80->80, 0.0.0.0:443->443, 0.0.0.0:8080->8080, 443/udp
coolify         coollabsio/coolify   0.0.0.0:8000->8080
coolify-db, coolify-redis, coolify-sentinel, coolify-realtime
predpol-db      postgis/postgis:17-3.5   127.0.0.1:5432->5432 ← database PENGEMBANGAN
```

```text
nama network milik proxy : coolify
entrypoint Traefik       : http (:80) dan https (:443)
penerbit sertifikat      : certificatesresolvers.letsencrypt (tantangan HTTP)
provider                 : docker, exposedbydefault=false
```

Tiga akibat yang menentukan seluruh susunan ini:

1. **Jangan pernah mengikat port 80 atau 443 ke host.** Container yang mencobanya tidak
   akan pernah menyala — port sudah dipakai. Karena itu JALUR A tidak memuat proxy
   sendiri sama sekali.
2. **Perutean diatur lewat label Traefik**, bukan lewat berkas konfigurasi proxy.
   Karena `exposedbydefault=false`, container yang tidak memasang `traefik.enable=true`
   memang tidak akan dirutekan — itulah sebabnya `api` dan `db` aman secara bawaan.
3. **Sertifikat HTTPS bukan urusan kita.** Traefik-nya Coolify yang menerbitkan dan
   memperbaruinya lewat resolver `letsencrypt`. Menambahkan certbot/acme sendiri untuk
   domain yang sama hanya akan membuat keduanya saling menggagalkan.

### JALUR B — server bersih tanpa Coolify

Disediakan untuk keadaan yang berbeda: server lain, pemindahan aplikasi, atau kebutuhan
menjalankan demo tanpa bergantung pada perangkat lunak pihak lain. Di jalur ini reverse
proxy-nya milik kita sendiri (Caddy), yang mengikat port 80 dan 443 dan mengurus
sertifikatnya sendiri.

**Menjalankan JALUR B di server demo ini akan gagal** dengan pesan
`bind: address already in use`. Itu bukan kerusakan, melainkan tanda bahwa jalur yang
dipilih salah.

### Ringkasan perbedaan perintah

| | JALUR A (dipakai) | JALUR B (alternatif) |
|---|---|---|
| Berkas tambahan | `docker-compose.coolify.yml` | `docker-compose.caddy.yml` |
| Port host yang diikat | tidak ada | 80, 443 |
| Penerbit sertifikat | Traefik-nya Coolify | Caddy |
| `ACME_EMAIL` di `.env.production` | tidak dipakai | wajib diisi |
| Network tambahan | `coolify` (sudah ada, `external`) | tidak ada |

---

## 2. PRASYARAT

### 2.1 Perangkat lunak

```bash
docker --version          # perlu Docker Engine 24 atau lebih baru
docker compose version    # perlu Compose v2
```

### 2.2 Hak akses Docker — sering terlewat

Perintah `docker` gagal dengan pesan berikut bila pengguna belum tergabung ke grup `docker`:

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

Perbaikannya:

```bash
sudo usermod -aG docker $USER
```

Lalu **keluar dan masuk kembali** ke server (`exit`, kemudian `ssh` lagi). Keanggotaan grup
baru berlaku pada sesi baru. Bila terpaksa harus bekerja pada sesi yang sedang berjalan,
setiap perintah dapat dibungkus:

```bash
sg docker -c "docker ps"
```

Periksa hasilnya:

```bash
docker info | grep -i "Server Version"
```

Bila baris versi server muncul, akses sudah benar.

### 2.3 Port — hanya relevan untuk JALUR B

JALUR A tidak mengikat port apa pun, jadi langkah ini dilewati.

Untuk JALUR B, port **80** dan **443** harus bebas dan terbuka di firewall:

```bash
sudo ss -lntp | grep -E ':80 |:443 '     # harus kosong
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Port 80 tetap diperlukan meski situs berjalan di HTTPS: Let's Encrypt memakainya untuk
memverifikasi kepemilikan domain.

### 2.4 Sumber daya server

Perkiraan minimum yang wajar: **2 vCPU, 4 GB RAM, 20 GB disk**. Bagian yang paling haus
memori adalah `docker compose build`. Perlu diingat Coolify dan enam containernya sudah
memakai sebagian sumber daya server ini.

---

## 3. MENGARAHKAN DOMAIN KE SERVER

Lakukan ini **lebih dahulu**, sebelum menjalankan aplikasi. Penerbitan sertifikat akan gagal
bila domain belum menunjuk ke server, dan kegagalan berulang dapat menabrak batas penerbitan
Let's Encrypt.

1. Cari alamat IP publik server:

   ```bash
   curl -s https://api.ipify.org; echo
   ```

2. Di panel penyedia domain, buat satu **A record**:

   | Kolom | Isi |
   |---|---|
   | Type | `A` |
   | Name / Host | `@` (artinya domain itu sendiri) |
   | Value / Points to | alamat IP dari langkah 1 |
   | TTL | biarkan default |

3. Tunggu penyebaran DNS (biasanya 5–30 menit), lalu pastikan sudah benar:

   ```bash
   dig +short DOMAIN-ANDA
   ```

   Keluarannya harus persis alamat IP server. **Jangan lanjut sebelum cocok.**

> Bila ingin `www.domain-anda` juga bekerja, tambahkan A record kedua dengan Name `www`,
> lalu tambahkan nama itu ke aturan `Host(...)` pada `docker-compose.coolify.yml`
> (JALUR A) atau ke `infra/docker/Caddyfile` (JALUR B).

---

## 4. MENYIAPKAN `.env.production`

### 4.1 Menyalin berkas contoh

Dari akar repository (`/home/kim/siintel`):

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

`chmod 600` membuat berkas hanya dapat dibaca pemiliknya. Berkas ini memuat kata sandi
database dan kunci sesi.

### 4.2 Membuat nilai acak

Jalankan dua perintah berikut dan **simpan keluarannya**:

```bash
# Kata sandi database — huruf dan angka saja
openssl rand -hex 24

# Kunci penanda tangan sesi (JWT_SECRET) — jauh lebih panjang dari 32 byte
openssl rand -base64 48
```

Bila `openssl` tidak tersedia:

```bash
python3 -c "import secrets; print(secrets.token_hex(24))"
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Mengapa panjang itu penting.** API sengaja **menolak menyala** bila `JWT_SECRET` kosong
atau lebih pendek dari 32 byte saat `APP_ENV=production`
(`apps/api/src/prediksi_presisi_api/config.py`). Kunci pendek membuat tanda tangan token
dapat ditebak (RFC 7518 §3.2). Container yang gagal start di sini adalah pengaman yang
bekerja, bukan kerusakan. Pesannya berbunyi:

```text
RuntimeError: JWT_SECRET wajib diisi pada lingkungan produksi.
```

**Mengapa kata sandi database harus huruf dan angka saja.** Nilai itu disusun menjadi URL
koneksi di dalam compose. Tanda seperti `@ : / # ?` akan memutus URL tersebut.

### 4.3 Mengisi berkas

```bash
nano .env.production
```

Yang wajib diisi:

| Variabel | Isi |
|---|---|
| `DOMAIN` | nama domain tanpa `https://`, mis. `prediksipresisi.id` |
| `POSTGRES_PASSWORD` | keluaran `openssl rand -hex 24` |
| `JWT_SECRET` | keluaran `openssl rand -base64 48` |
| `DEMO_REFERENCE_TIME` | lihat peringatan di bawah |
| `ACME_EMAIL` | **hanya untuk JALUR B**; boleh dikosongkan pada JALUR A |

**Peringatan tentang `DEMO_REFERENCE_TIME`.** Data sintetis berhenti pada 31 Desember 2025.
Bila dibiarkan kosong, aplikasi memakai waktu server yang sebenarnya, sehingga seluruh panel
"24 jam terakhir" dan "peringatan aktif" akan **kosong** saat paparan. Isi dengan waktu di
dalam rentang data:

```text
DEMO_REFERENCE_TIME=2025-12-30T09:00:00
```

Aplikasi menyatakan terbuka di antarmuka bahwa waktu acuan sedang dipakai — ini transparansi
yang disengaja (`services/clock.py`), dan justru itu yang membuat klaim tetap dapat
dipertanggungjawabkan saat ditanya penguji.

Simpan dengan `Ctrl+O`, `Enter`, lalu keluar dengan `Ctrl+X`.

### 4.4 Memeriksa isian tanpa menjalankan apa pun

```bash
docker compose --env-file .env.production \
  -f infra/docker/docker-compose.prod.yml \
  -f infra/docker/docker-compose.coolify.yml config >/dev/null && echo "Konfigurasi terbaca dengan benar."
```

Bila ada variabel wajib yang belum diisi, perintah ini berhenti dan menyebut namanya.

---

## 5. MENJALANKAN

Seluruh perintah di bawah dijalankan **dari akar repository**.

Karena setiap perintah selalu memerlukan tiga argumen yang sama, simpan singkatannya sekali
di awal sesi:

```bash
cd /home/kim/siintel

# JALUR A — server demo ini
alias predpol='docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml'

# JALUR B — server bersih tanpa Coolify (JANGAN dipakai di server demo)
# alias predpol='docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.caddy.yml'
```

> `alias` hanya berlaku selama sesi terminal itu. Bila sudah ada script di `package.json`
> (lihat §12), gunakan `pnpm prod:up` dan seterusnya sebagai gantinya.

### 5.1 Membangun image

```bash
predpol build
```

Pembangunan pertama memakan waktu beberapa menit karena mengunduh dependensi Python dan
Node. Pembangunan berikutnya jauh lebih cepat.

### 5.2 Menyalakan

```bash
predpol up -d
```

`-d` berarti berjalan di latar belakang; terminal dapat ditutup tanpa mematikan aplikasi.

### 5.3 Memeriksa kondisi

```bash
predpol ps
```

Kolom `STATUS` untuk `db` dan `api` harus menunjukkan `healthy`. Bila `web` masih
`starting`, tunggu sekitar 20 detik lalu ulangi.

Pastikan pula container `web` benar-benar tersambung ke jaringan proxy:

```bash
docker network inspect coolify --format '{{range .Containers}}{{.Name}} {{end}}'
```

Nama `predpol-prod-web` harus muncul di antara container Coolify. Bila tidak, Traefik tidak
akan pernah melihatnya.

### 5.4 Sertifikat HTTPS

Pada JALUR A, penerbitan sertifikat dikerjakan Traefik-nya Coolify dan berlangsung otomatis
saat permintaan HTTPS pertama untuk domain tersebut tiba. Bila situs belum dapat dibuka,
lihat log proxy milik Coolify — bukan log aplikasi kita:

```bash
docker logs --tail 100 coolify-proxy
```

### 5.5 Membuka aplikasi

```text
https://DOMAIN-ANDA
```

Pada tahap ini halaman masuk sudah tampil, tetapi **belum ada data dan belum ada akun yang
dapat dipakai**. Lanjut ke §6.

### 5.6 Alternatif: mendaftarkan aplikasi lewat antarmuka Coolify

Cara di atas menjalankan compose secara langsung; Traefik mengenalinya dari label, dan itu
sudah cukup. Bila lebih nyaman mengelola lewat antarmuka Coolify (menambahkan domain,
tombol redeploy, riwayat deployment), aplikasi ini juga dapat didaftarkan sebagai resource
bertipe **Docker Compose** di Coolify, dengan `.env.production` disalin ke bagian
Environment Variables miliknya. Pada cara itu Coolify yang menuliskan label dan domainnya
sendiri, sehingga `docker-compose.coolify.yml` tidak perlu diikutkan.

Untuk paparan, cara langsung pada §5.1–5.3 lebih sedikit bagiannya, jadi lebih sedikit pula
yang dapat salah.

---

## 6. MIGRATION DAN SEED DI SERVER

Dijalankan **satu kali** setelah menyala pertama, dan diulang hanya bila database dikosongkan.

### 6.1 Membuat struktur tabel

```bash
predpol exec api alembic upgrade head
```

> Seluruh perintah pada bab ini juga tersedia sebagai script pnpm, yang sudah
> membawa `--env-file` dan kedua berkas compose: `pnpm prod:migrate`,
> `pnpm prod:seed`, `pnpm prod:password -- demo.pimpinan`, `pnpm prod:users`,
> `pnpm prod:up`, `pnpm prod:ps`, `pnpm prod:logs`. Pakai yang mana pun yang
> lebih nyaman — keduanya menjalankan hal yang persis sama.

Perintah ini membuat 20 tabel, ekstensi PostGIS, seluruh constraint, index, dan trigger.
Aman diulang: migration yang sudah diterapkan akan dilewati.

Periksa hasilnya:

```bash
predpol exec api alembic current
```

### 6.2 Mengisi data demo

```bash
predpol exec api python -m prediksi_presisi_api.seeding all
```

Perintah ini memuat seluruh data sintetis dari `data/sample/` — lokasi, kejadian, prediksi,
peringatan, rekomendasi, keputusan, dan data evaluasi. Ringkasan jumlah baris per tabel akan
ditampilkan di akhir.

### 6.3 Memastikan berhasil

```bash
predpol exec api python -m prediksi_presisi_api.cli list-users
```

Enam akun demo harus muncul, seluruhnya dengan kredensial **`terkunci`**. Itu memang
disengaja — lanjut ke §7.

---

## 7. MENETAPKAN PASSWORD AKUN DEMO

### 7.1 Mengapa akun sengaja terkunci

Berkas seed **tidak pernah memuat password**. Akun hasil seed berstatus terkunci sampai
password ditetapkan langsung di server. Dengan begitu tidak ada satu pun kredensial yang
tersimpan di repository, dan tidak ada password bawaan yang diam-diam terbawa ke instalasi
mana pun.

> ### ⚠ WAJIB SEBELUM DIBUKA KE PUBLIK
>
> Password uji **`Paparan#Sespimma2026`** dipakai pada database **pengembangan** untuk
> akun `demo.pimpinan`, `demo.polsek`, dan `demo.analyst`. Nilai itu sudah tertulis
> dalam percakapan kerja, jadi harus dianggap **sudah bocor**: jangan pernah dipakai
> di server ini, dan gantilah juga di database pengembangan bila mesinnya dapat
> dijangkau dari luar. Gunakan nilai baru yang berbeda untuk setiap akun.

### 7.2 Menetapkan password

Untuk setiap akun, jalankan:

```bash
predpol exec api python -m prediksi_presisi_api.cli set-password demo.pimpinan
```

Perintah akan meminta password dua kali. **Ketikan tidak terlihat di layar** — itu normal,
bukan keyboard yang mati. Password minimal 12 karakter.

Ulangi untuk keenam akun:

```bash
predpol exec api python -m prediksi_presisi_api.cli set-password demo.pimpinan
predpol exec api python -m prediksi_presisi_api.cli set-password demo.commandcenter
predpol exec api python -m prediksi_presisi_api.cli set-password demo.analyst
predpol exec api python -m prediksi_presisi_api.cli set-password demo.fungsi
predpol exec api python -m prediksi_presisi_api.cli set-password demo.polsek
predpol exec api python -m prediksi_presisi_api.cli set-password demo.admin
```

> **Hubungannya dengan `pnpm user:password`.** Keduanya memanggil program yang sama,
> `prediksi_presisi_api.cli set-password`. Bedanya hanya tempat: `pnpm user:password`
> dijalankan dari mesin pengembangan terhadap database pengembangan, sedangkan di server
> produksi database sengaja tidak memiliki port yang terbuka — sehingga perintah harus
> dijalankan **di dalam container** seperti di atas. Pemeriksaan panjang password dan cara
> penyimpanan hash-nya identik.

### 7.3 Memeriksa hasilnya

```bash
predpol exec api python -m prediksi_presisi_api.cli list-users
```

Kolom kredensial harus berubah dari `terkunci` menjadi `aktif`.

Catat pasangan akun dan password pada catatan luring (bukan di dalam repository ini), dan
siapkan hanya akun yang benar-benar akan dipakai saat paparan.

---

## 8. MENGHENTIKAN, MENYALAKAN ULANG, DAN MELIHAT LOG

### 8.1 Menghentikan sementara

```bash
predpol stop
```

Container berhenti, **data tetap utuh**. Menyalakan lagi:

```bash
predpol start
```

### 8.2 Menghentikan dan membersihkan container

```bash
predpol down
```

Container dihapus, tetapi **volume data tetap aman**. Ini perintah yang benar sebelum
memasang versi baru.

> ### ⚠ JANGAN memakai `down -v`
>
> Tambahan `-v` **menghapus volume**, artinya seluruh isi database hilang. Tidak ada
> konfirmasi dan tidak ada pembatalan.
>
> Perlu diketahui juga: `down` **tidak** menyentuh network `coolify` karena network itu
> ditandai `external` — milik Coolify, bukan milik kita.

### 8.3 Memasang versi baru dari kode terbaru

```bash
git pull
predpol build
predpol up -d
predpol exec api alembic upgrade head    # bila ada migration baru
```

### 8.4 Melihat log

```bash
predpol logs -f            # seluruh layanan
predpol logs -f api        # hanya API
predpol logs -f web        # hanya web
predpol logs --tail 100 api

docker logs --tail 100 coolify-proxy   # JALUR A: masalah HTTPS/perutean terlihat di sini
predpol logs -f proxy                  # JALUR B: proxy milik kita sendiri
```

`Ctrl+C` menghentikan tampilan log, bukan aplikasinya.

### 8.5 Memeriksa kesehatan tanpa peramban

```bash
predpol exec api python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').read().decode())"
```

Balasannya menyebut status aplikasi **dan** status database beserta nomor revisi migration.

---

## 9. BACKUP DAN PEMULIHAN DATABASE

### 9.1 Membuat backup

```bash
mkdir -p ~/backup-predpol
predpol exec -T db pg_dump -U predpol -d prediksi_presisi -Fc \
  > ~/backup-predpol/predpol-$(date +%Y%m%d-%H%M).dump
```

Penjelasan singkat:

| Bagian | Artinya |
|---|---|
| `exec -T` | tanpa terminal interaktif, supaya keluaran dapat dialihkan ke berkas |
| `-Fc` | format terkompresi milik PostgreSQL, lebih kecil dan lebih fleksibel |
| `$(date ...)` | nama berkas otomatis memuat tanggal dan jam |

Periksa berkasnya benar-benar terisi:

```bash
ls -lh ~/backup-predpol/
```

Ukuran beberapa ratus KB sampai beberapa MB adalah wajar. Ukuran **0 byte berarti backup
gagal** — periksa pesan kesalahan.

**Ambil backup tepat sebelum hari paparan**, dan salin satu berkasnya ke luar server
(laptop atau penyimpanan lain). Backup yang hanya ada di server yang sama tidak menolong
bila server itu yang bermasalah.

### 9.2 Memulihkan dari backup

```bash
predpol exec -T db pg_restore -U predpol -d prediksi_presisi --clean --if-exists \
  < ~/backup-predpol/predpol-20260901-1030.dump
```

`--clean --if-exists` menghapus objek lama sebelum memuat ulang. **Isi database saat ini akan
ditimpa.** Jalankan hanya bila memang itu yang diinginkan.

Setelah pemulihan, periksa:

```bash
predpol exec api alembic current
predpol exec api python -m prediksi_presisi_api.cli list-users
```

### 9.3 Membangun ulang dari nol

Bila database perlu dikosongkan sepenuhnya dan disusun ulang dari kode:

```bash
predpol down
docker volume rm prediksi-presisi-prod_db-data     # menghapus SELURUH data
predpol up -d
predpol exec api alembic upgrade head
predpol exec api python -m prediksi_presisi_api.seeding all
```

Password akun demo ikut hilang dan harus ditetapkan ulang (§7).

---

## 10. BILA ADA MASALAH

| Gejala | Kemungkinan sebab | Tindakan |
|---|---|---|
| `permission denied ... docker.sock` | pengguna belum di grup `docker` | §2.2, lalu masuk ulang |
| `bind: address already in use` pada 80/443 | menjalankan JALUR B di server yang sudah memakai Coolify | pakai JALUR A (§1) |
| Domain tidak menemukan aplikasi (503 dari proxy) | `web` tidak tersambung network `coolify`, atau label Traefik tidak terbaca | `docker network inspect coolify`, lalu `docker logs coolify-proxy` |
| Sertifikat tidak terbit | A record belum menunjuk ke server | `dig +short DOMAIN-ANDA` |
| Container `api` berhenti terus | `JWT_SECRET` kosong atau kurang dari 32 byte | `predpol logs api`, lalu perbaiki `.env.production` (§4.2) |
| Halaman tampil, tetapi seluruh panel kosong | migration/seed belum dijalankan, atau `DEMO_REFERENCE_TIME` kosong | §6 dan §4.3 |
| Tidak bisa masuk dengan akun demo | password belum ditetapkan | §7 |
| Perubahan kode tidak muncul | image belum dibangun ulang | `predpol build && predpol up -d` |

Untuk melihat pesan kesalahan yang sebenarnya, selalu mulai dari:

```bash
predpol ps
predpol logs --tail 100
```

---

## 11. DAFTAR PERIKSA SEBELUM PAPARAN

Kerjakan berurutan pada **H-1**, bukan pada pagi hari paparan.

### Akses dan keamanan

- [ ] `https://DOMAIN-ANDA` terbuka dan gembok HTTPS muncul di peramban
- [ ] `http://DOMAIN-ANDA` otomatis dialihkan ke HTTPS
- [ ] Password uji `PaparanTaskap#2026` **sudah tidak berlaku** di server ini
- [ ] Keenam akun demo berstatus `aktif` dengan password baru yang tercatat luring
- [ ] `.env.production` berizin `600` dan tidak muncul di `git status`
- [ ] Halaman `https://DOMAIN-ANDA/docs` **tidak** dapat diakses (dimatikan saat `APP_ENV=production`)
- [ ] `predpol ps` menunjukkan **tidak ada** port host yang dipublish oleh `db`, `api`, maupun `web`
- [ ] Container `predpol-db` sudah dibuat ulang (`pnpm db:down && pnpm db:up`) agar
      pengikatan `127.0.0.1` benar-benar berlaku (lihat §12)

### Data dan tampilan

- [ ] `predpol exec api alembic current` menunjukkan revisi terbaru
- [ ] `DEMO_REFERENCE_TIME` terisi dan panel "24 jam terakhir" tidak kosong
- [ ] Dashboard, peta, warning center, rekomendasi, dan halaman evaluasi terbuka tanpa error
- [ ] Masuk dan keluar berhasil pada minimal dua peran berbeda
- [ ] Angka di layar cocok dengan isi database (bukan angka yang ditulis di kode)

### Kesiapan operasional

- [ ] Backup terbaru sudah dibuat **dan sudah disalin ke luar server**
- [ ] `predpol ps` menunjukkan seluruh container `healthy`
- [ ] Server diuji sekali `reboot`, lalu container menyala sendiri (`restart: unless-stopped`)
- [ ] Perangkat dan jaringan yang dipakai saat paparan sudah dicoba membuka domain tersebut
- [ ] Rencana cadangan bila jaringan lokasi paparan bermasalah sudah disiapkan

### Kejujuran materi

- [ ] Siap menyatakan terbuka bahwa data bersifat **sintetis**, dan bahwa bobot serta
      threshold berstatus `DEMO / PROPOSED`, bukan hasil model terlatih
      (`docs/09` §5, CLAUDE.md §11)
- [ ] Siap menunjukkan bahwa rantai keputusan bersifat human-in-the-loop: rekomendasi
      bukan perintah, dan tindakan operasional memerlukan persetujuan manusia

---

## 12. CATATAN KEAMANAN YANG BELUM SELESAI

Dua hal ditemukan saat menyiapkan deployment ini:

1. **Database pengembangan mempublikasikan port 5432 ke semua antarmuka.** Container
   `predpol-db` dari `infra/docker/docker-compose.yml` mengikat `0.0.0.0:5432->5432`, dengan
   kredensial bawaan `predpol/predpol` yang tertulis di `.env.example`.

   **Seberapa parah — diperiksa, bukan diduga.** Alamat IPv4 global mesin ini adalah
   `10.3.3.87`, yaitu alamat privat RFC1918 di belakang NAT, dan `ufw` berstatus aktif.
   Jadi database ini **tidak** terjangkau langsung dari internet; yang dapat mencobanya
   adalah host lain di jaringan lokal yang sama. Itu tetap lebih luas daripada yang
   diperlukan, tetapi bukan keadaan darurat.

   **Sudah diperbaiki di berkas**: pemetaan port kini `127.0.0.1:${POSTGRES_PORT:-5432}:5432`.
   Perubahan itu baru berlaku ketika container dibuat ulang:

   ```bash
   pnpm db:down && pnpm db:up
   ```

   Data tersimpan di volume bernama `prediksi-presisi_db-data`, sehingga tidak hilang.
   **Ini bukan container produksi** — susunan produksi tidak membuka port database sama sekali.

2. **Aplikasi Coolify terbuka pada port 8000** (`0.0.0.0:8000->8080`). Itu bawaan Coolify,
   bukan buatan proyek ini, tetapi pantas dibatasi ke alamat tertentu bila server dipakai
   untuk paparan resmi.

---

## 13. RINGKASAN PERINTAH

Bila script produksi sudah ditambahkan ke `package.json` root, bentuk pendeknya:

| Keperluan | Perintah pendek | Perintah lengkap (JALUR A) |
|---|---|---|
| Membangun image | `pnpm prod:build` | `docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml build` |
| Menyalakan | `pnpm prod:up` | `... up -d` |
| Menghentikan | `pnpm prod:down` | `... down` |
| Melihat kondisi | `pnpm prod:ps` | `... ps` |
| Melihat log | `pnpm prod:logs` | `... logs -f` |
| Migration | `pnpm prod:migrate` | `... exec api alembic upgrade head` |
| Seed | `pnpm prod:seed` | `... exec api python -m prediksi_presisi_api.seeding all` |
| Password akun | `pnpm prod:password demo.pimpinan` | `... exec api python -m prediksi_presisi_api.cli set-password demo.pimpinan` |
| Daftar akun | `pnpm prod:users` | `... exec api python -m prediksi_presisi_api.cli list-users` |
| Konfigurasi (JALUR B) | `pnpm prod:caddy:up` | `docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.caddy.yml up -d` |
