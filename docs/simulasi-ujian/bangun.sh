#!/usr/bin/env bash
# Membangun PDF dua lintasan: cetak, baca nomor halaman tiap judul, cetak ulang dengan daftar isi terisi.
#   PY=/jalur/python-yang-punya-pypdf bash bangun.sh
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"
export LD_LIBRARY_PATH="$HOME/.local/chromium-libs/root/usr/lib/x86_64-linux-gnu"
CHROME="$HOME/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
cetak() { "$CHROME" --no-sandbox --allow-file-access-from-files --no-pdf-header-footer --print-to-pdf=Simulasi-Ujian-SIGAP.pdf "file://$PWD/simulasi-ujian-sigap.html" 2>/dev/null; }
rm -f halaman.json
python3 buat.py && cetak && "$PY" nomor.py Simulasi-Ujian-SIGAP.pdf
python3 buat.py && cetak && "$PY" nomor.py Simulasi-Ujian-SIGAP.pdf
