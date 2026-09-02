"""Waktu acuan untuk seluruh test.

Dataset sintetis berhenti pada 31 Desember 2025, dan aplikasi dijalankan dengan
`DEMO_REFERENCE_TIME` yang menggeser "sekarang" ke ujung dataset itu (keputusan SDL-16,
`docs/10` §6). Produksi memakainya; sampai berkas ini ada, test **tidak**.

Akibatnya tidak terlihat sebagai kegagalan: seluruh panel "24 jam terakhir", "sepekan
terakhir", dan "peringatan aktif" dijawab kosong saat diuji, sehingga test yang memeriksa
isinya lulus tanpa memeriksa apa pun. Cacat pada perhitungan jendela waktu — jendela yang
meleset sehari, pembanding yang tertukar, penyaring yang tidak berpengaruh — akan lolos
seluruhnya.

Nilainya disetel dengan `setdefault`, jadi menjalankan test terhadap waktu sebenarnya tetap
mungkin dengan mengisi variabel itu lebih dulu.
"""

from __future__ import annotations

import os

#: Sama persis dengan `.env.production` — test menguji konfigurasi yang benar-benar dipakai.
os.environ.setdefault("DEMO_REFERENCE_TIME", "2025-12-31T21:00:00+07:00")
