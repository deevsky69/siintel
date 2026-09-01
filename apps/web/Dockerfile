# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# PREDIKSI PRESISI — image Web (Next.js 15, mode produksi)
#
# KONTEKS BUILD ADALAH AKAR REPOSITORY: lockfile pnpm dan pnpm-workspace.yaml ada di
# akar, dan Next.js memakai akar workspace itu untuk menelusuri berkas saat membuat
# keluaran `standalone`.
#
# PRASYARAT YANG BELUM TERPENUHI:
#   apps/web/next.config.ts HARUS memuat `output: "standalone"`.
#   Berkas itu sengaja tidak diubah oleh penyiapan ini. Selama baris tersebut belum
#   ditambahkan, build akan berhenti dengan pesan yang jelas pada tahap `builder`.
#
# Build (dari akar repository):
#   docker build -f apps/web/Dockerfile -t prediksi-presisi-web .
# ---------------------------------------------------------------------------

ARG NODE_IMAGE=node:22-bookworm-slim

# ---------- Tahap 1 — dependensi ----------
FROM ${NODE_IMAGE} AS deps

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    CI=1

RUN corepack enable

WORKDIR /app

# Manifest lebih dulu agar lapisan pemasangan dipakai ulang selama lockfile tidak berubah.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json

# devDependencies tetap dipasang di sini: TypeScript, Tailwind, dan PostCSS
# dibutuhkan saat `next build`. Keduanya tidak ikut ke image akhir.
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile

# ---------- Tahap 2 — build ----------
FROM deps AS builder

WORKDIR /app

COPY apps/web ./apps/web

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

RUN pnpm --filter @prediksi-presisi/web build

# Kegagalan yang dapat dibaca lebih baik daripada COPY yang gagal tanpa penjelasan.
# Dua kemungkinan dibedakan di sini karena penyebabnya berbeda:
#   - tidak ada .next/standalone sama sekali  -> next.config.ts belum diubah
#   - ada, tetapi server.js tidak di apps/web -> akar penelusuran workspace berbeda
RUN if [ ! -d apps/web/.next/standalone ]; then \
      echo ""; \
      echo "GAGAL: keluaran standalone Next.js tidak ada."; \
      echo "Tambahkan baris berikut ke apps/web/next.config.ts, lalu build ulang:"; \
      echo "    output: \"standalone\","; \
      echo ""; \
      exit 1; \
    elif [ ! -f apps/web/.next/standalone/apps/web/server.js ]; then \
      echo ""; \
      echo "GAGAL: server.js tidak berada di .next/standalone/apps/web/."; \
      echo "Isi direktori standalone yang sebenarnya:"; \
      find apps/web/.next/standalone -maxdepth 3 -name server.js; \
      echo "Sesuaikan baris COPY pada tahap runtime Dockerfile ini."; \
      echo ""; \
      exit 1; \
    fi

# ---------- Tahap 3 — image yang benar-benar dijalankan ----------
FROM ${NODE_IMAGE} AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

# Pengguna `node` (uid 1000) sudah tersedia pada image resmi Node; tidak perlu dibuat.
# Keluaran standalone sudah memuat node_modules seperlunya — pnpm tidak dibutuhkan lagi.
COPY --from=builder --chown=node:node /app/apps/web/.next/standalone ./
COPY --from=builder --chown=node:node /app/apps/web/.next/static ./apps/web/.next/static

USER node

EXPOSE 3000

# `/masuk` adalah satu-satunya halaman yang boleh diakses tanpa sesi (src/middleware.ts),
# jadi halaman inilah penanda "server web hidup" yang benar.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=6 \
  CMD node -e "fetch('http://127.0.0.1:3000/masuk').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "apps/web/server.js"]
