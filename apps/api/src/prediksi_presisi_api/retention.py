"""Menjalankan masa retensi lampiran laporan masyarakat.

    uv run python -m prediksi_presisi_api.retention

Dijalankan terjadwal (cron harian). Ia melakukan dua hal:

1. **Menghapus berkas lampiran** yang laporannya sudah selesai lebih dari
   `RETENTION_DAYS_AFTER_CLOSED` hari. Barisnya dipertahankan beserta `purged_at`, sehingga
   jejak bahwa penghapusan itu dijalankan tetap ada — menghapus barisnya berarti menghapus
   juga buktinya.

2. **Membuang titipan unggahan** yang tidak pernah dipakai. Handle yang diterbitkan tetapi
   laporannya tidak jadi dikirim akan menumpuk selamanya kalau tidak dibersihkan, dan kanal
   publik akan menjadi tempat penitipan berkas.

MENGAPA PERINTAH TERPISAH, BUKAN TUGAS LATAR DI DALAM API

    Penghapusan data harus dapat dijalankan, dilihat hasilnya, dan diulang oleh manusia.
    Tugas latar di dalam proses API menjalankan penghapusan tanpa ada yang tahu ia berjalan,
    berhenti diam-diam bila prosesnya dijalankan ulang di tengah jalan, dan berlipat ganda
    bila kelak ada replika kedua.

Perintah ini menulis jejak audit tanpa `user_id`: tidak ada pengguna di balik peristiwa ini,
dan mengarangnya akan membuat jejak audit menyatakan sesuatu yang tidak terjadi.
"""

from __future__ import annotations

import logging
import sys

from .db import get_session_factory
from .services import attachments, audit, clock

logger = logging.getLogger("prediksi_presisi.retention")


def run() -> int:
    """Menjalankan satu putaran retensi. Mengembalikan jumlah berkas yang dihapus."""
    now = clock.reference_now()

    orphans = attachments.sweep_staging(now)
    if orphans:
        logger.info("titipan unggahan yang tidak terpakai dibuang: %d", orphans)

    with get_session_factory()() as session:
        purged = attachments.purge_expired(session, now)
        if purged:
            audit.record(
                session,
                action="PURGE_CITIZEN_REPORT_ATTACHMENTS",
                resource_type="citizen_report_attachment",
                result=audit.RESULT_SUCCESS,
                user_id=None,
                resource_id=None,
                detail={
                    "purged": len(purged),
                    "retention_days_after_closed": attachments.RETENTION_DAYS_AFTER_CLOSED,
                },
            )
        session.commit()

    logger.info("lampiran yang berkasnya dihapus: %d", len(purged))
    return len(purged)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    purged = run()
    print(f"berkas lampiran dihapus: {purged}")
    sys.exit(0)


if __name__ == "__main__":
    main()
