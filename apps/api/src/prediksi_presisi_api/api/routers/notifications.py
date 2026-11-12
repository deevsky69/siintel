"""Notifikasi — antrean pekerjaan pengguna, bukan kabar berita (TASK 164).

Permintaan pemilik proyek, 4 September 2026: penanda di pojok kanan atas yang isinya
**sesuai fungsi masing-masing peran**.

## Satu aturan yang menentukan seluruh modul ini

**Notifikasi adalah hal yang menunggu Anda kerjakan — bukan hal yang terjadi.**

Bedanya menentukan. Umpan "apa yang terjadi" akan sama bagi semua orang, terisi terus, dan
setelah dua hari tidak dibaca siapa pun; setiap orang belajar bahwa lencananya selalu merah
dan berhenti melihatnya. Antrean pekerjaan tidak begitu: ia menjadi nol ketika pekerjaannya
selesai, dan angka nol itulah yang membuat angka bukan-nol berarti sesuatu.

Karena itu tiap sumber di bawah diikat ke **permission tindakan**, bukan permission baca.
Seorang Pimpinan tidak diberi tahu ada laporan warga belum diverifikasi — ia tidak dapat
memverifikasinya, dan memberitahunya hanya menambah kecemasan tanpa jalan keluar. Sebaliknya
petugas Polsek tidak diberi tahu ada rekomendasi menunggu keputusan, sebab yang memutuskan
bukan dia.

Hasilnya berbeda-beda menurut peran, dan itu memang yang diminta:

```text
Pimpinan       produk bulanan menunggu penetapan · buletin menunggu persetujuan
Analis         draf produk bulanan belum dikirim
Polsek         permintaan bantuan darurat (panic)
Fungsi         (tidak ada antrean selain darurat)
Administrator  darurat · laporan warga belum diverifikasi · ulasan menunggu moderasi · draf produk
```

12 November 2026 (catatan 179): kelompok rantai harian — peringatan, rekomendasi harian,
prediksi draf, keputusan belum ditindaklanjuti, rencana patroli — dihapus dari antrean.
Layarnya sudah keluar dari menu sejak 6 November, dan lonceng yang masih menunjuk ke sana
menyeret pengguna ke rantai yang tidak lagi dipaparkan.

## Yang sengaja TIDAK dikerjakan di sini

Tidak ada penyimpanan "sudah dibaca". Notifikasi di sini **dihitung ulang dari keadaan
sebenarnya** setiap kali diminta, sehingga tidak mungkin menunjukkan pekerjaan yang sudah
selesai — dan tidak ada jalan bagi seseorang untuk menghilangkan pekerjaannya sendiri dari
daftar dengan menandainya terbaca. Penanda terbaca adalah kenyamanan yang, pada antrean
tugas, berubah menjadi cara melupakan tugas.

Seluruh sumber dibatasi cakupan wilayah di query, sama seperti layar lain.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import AreaReview, Bulletin, CitizenReport, Location, MonthlyProduct, PanicEvent
from ...services import clock
from ...services import monthly_product as products
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from .public_intake import load_urgent_categories

router = APIRouter(tags=["notifikasi"])

#: Banyaknya butir contoh yang dibawa tiap sumber. Daftar yang lebih panjang berhenti
#: menjadi pengingat dan berubah menjadi layar daftar — yang memang sudah ada menunya.
SAMPLE_LIMIT = 3

NOTIFICATION_BASIS = (
    "Notifikasi di sini adalah pekerjaan yang MENUNGGU ANDA, bukan kabar tentang apa yang "
    "terjadi. Tiap sumber diikat ke permission tindakan, bukan permission baca: yang tidak "
    "dapat Anda kerjakan tidak ditampilkan, karena angka yang tidak dapat Anda selesaikan "
    "hanya menjadi kecemasan tanpa jalan keluar. Jumlahnya dihitung ulang dari keadaan "
    "sebenarnya setiap kali dibuka — tidak ada penanda 'sudah dibaca', sebab pada antrean "
    "tugas penanda seperti itu berubah menjadi cara melupakan tugas."
)


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


def _holds(current: CurrentUser, permission: str) -> bool:
    """Benar bila pengguna memegang permission tersebut."""
    return current.permissions.allows(permission)


@router.get("/notifications", summary="Antrean pekerjaan yang menunggu pengguna")
def notifications(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    """Pekerjaan yang menunggu pengguna ini, menurut apa yang dapat ia kerjakan.

    `dashboard:read` dipakai sebagai gerbang karena setiap peran memilikinya — gerbangnya
    bukan yang menentukan isi. Yang menentukan adalah permission tindakan yang diperiksa
    per sumber di bawah, dan itulah sebabnya dua peran yang sama-sama lolos gerbang ini
    tetap menerima daftar yang berbeda.
    """
    groups: list[dict[str, Any]] = []

    # --- Permintaan bantuan darurat (8 Oktober 2026) — SELALU paling atas ---------------
    # Diikat ke `panic:read`, bukan permission tindakan: keputusan pemilik proyek adalah
    # Pimpinan ikut diberi tahu meski yang menerima adalah Polsek/Administrator.
    if _holds(current, "panic:read"):
        polsek = jurisdiction_filter(current, "panic:read")
        base = select(PanicEvent).where(PanicEvent.status == "OPEN")
        if polsek is not None:
            base = base.join(Location, Location.location_id == PanicEvent.location_id).where(
                Location.polsek == polsek
            )
        panic_rows = session.scalars(
            base.order_by(PanicEvent.pressed_at.desc()).limit(SAMPLE_LIMIT)
        ).all()
        panic_total = session.scalar(select(func.count()).select_from(base.subquery()))
        groups.append(
            {
                "kind": "PANIC",
                "title": "Permintaan bantuan darurat",
                "action": "Terima dan tindak lanjuti sekarang",
                "href": "/ops/panic",
                "total": int(panic_total or 0),
                # Selalu disorot bila ada isinya (9 Oktober 2026): layar mengedipkannya.
                "urgent": int(panic_total or 0) > 0,
                "urgent_total": int(panic_total or 0),
                "items": [
                    {
                        "code": event.code,
                        "headline": (
                            f"{event.location.kelurahan}, {event.location.kecamatan}"
                            if event.location
                            else "Lokasi tidak dikirim"
                        ),
                        "detail": (
                            f"ditekan {event.pressed_at.astimezone(clock.JAKARTA):%H:%M} WIB"
                            + (f" · {event.note}" if event.note else "")
                        ),
                    }
                    for event in panic_rows
                ],
            }
        )

    # --- Produk bulanan (Modul 4 mekanisme; dua tahap sejak 10 November 2026) -----------
    # Pimpinan: produk yang menunggu penetapan. Analis/Administrator: draf yang belum
    # diperiksa dan dikirim. Keduanya permission tindakan, bukan permission baca.
    if _holds(current, "monthly_product:decide"):
        rows = session.scalars(
            select(MonthlyProduct)
            .where(MonthlyProduct.status.in_(products.AWAITING_DECISION))
            .order_by(MonthlyProduct.target_month.desc())
            .limit(SAMPLE_LIMIT)
        ).all()
        total = session.scalar(
            select(func.count())
            .select_from(MonthlyProduct)
            .where(MonthlyProduct.status.in_(products.AWAITING_DECISION))
        )
        groups.append(
            {
                "kind": "MONTHLY_PRODUCT",
                "title": "Produk bulanan menunggu penetapan Anda",
                "action": "Tetapkan jumlah dan kelurahan prioritas",
                "href": "/ops/produk-bulanan",
                "total": int(total or 0),
                "items": [
                    {
                        "code": product.target_month.isoformat()[:7],
                        "headline": f"Produk bulan {product.target_month.isoformat()[:7]}",
                        "detail": "Sudah diperiksa Analis; menunggu penetapan",
                    }
                    for product in rows
                ],
            }
        )
    elif _holds(current, "monthly_product:draft"):
        rows = session.scalars(
            select(MonthlyProduct)
            .where(MonthlyProduct.status == "DRAFT")
            .order_by(MonthlyProduct.target_month.desc())
            .limit(SAMPLE_LIMIT)
        ).all()
        total = session.scalar(
            select(func.count()).select_from(MonthlyProduct).where(MonthlyProduct.status == "DRAFT")
        )
        groups.append(
            {
                "kind": "MONTHLY_PRODUCT",
                "title": "Draf produk bulanan belum dikirim",
                "action": "Periksa usulan lalu kirim ke Pimpinan",
                "href": "/ops/produk-bulanan",
                "total": int(total or 0),
                "items": [
                    {
                        "code": product.target_month.isoformat()[:7],
                        "headline": f"Draf bulan {product.target_month.isoformat()[:7]}",
                        "detail": "Terima, perbaiki, atau tolak tiap usulan dengan alasan",
                    }
                    for product in rows
                ],
            }
        )

    # --- Buletin mingguan menunggu persetujuan Pimpinan ----------------------------------
    if _holds(current, "bulletin:approve"):
        rows = session.scalars(
            select(Bulletin)
            .where(Bulletin.status == "DRAFT")
            .order_by(Bulletin.week_start.desc(), Bulletin.kelurahan)
            .limit(SAMPLE_LIMIT)
        ).all()
        total = session.scalar(
            select(func.count()).select_from(Bulletin).where(Bulletin.status == "DRAFT")
        )
        groups.append(
            {
                "kind": "BULLETIN",
                "title": "Buletin kelurahan menunggu persetujuan",
                "action": "Setujui agar bot mengirimnya",
                "href": "/ops/buletin",
                "total": int(total or 0),
                "items": [
                    {
                        "code": str(bulletin.bulletin_id),
                        "headline": (
                            f"{bulletin.kelurahan} · minggu {bulletin.week_start.isoformat()}"
                        ),
                        "detail": "Disusun sistem dari kejadian minggu lalu",
                    }
                    for bulletin in rows
                ],
            }
        )

    # --- Laporan masyarakat yang belum diverifikasi -----------------------------------
    # Diikat ke `citizen_report:triage` (9 Oktober 2026): yang mengubah status laporan
    # hanya Administrator, dan antrean ini adalah daftar pekerjaan, bukan umpan berita.
    if _holds(current, "citizen_report:triage"):
        polsek = jurisdiction_filter(current, "citizen_report:triage")
        # Laporan tanpa lokasi tidak dapat dibebankan ke wilayah mana pun; pengguna
        # ber-cakupan tidak menerimanya, sebab menampilkannya berarti menebak.
        query = select(CitizenReport).where(CitizenReport.status == "RECEIVED")
        counter = (
            select(func.count())
            .select_from(CitizenReport)
            .where(CitizenReport.status == "RECEIVED")
        )
        if polsek is not None:
            query = query.join(Location, Location.location_id == CitizenReport.location_id).where(
                Location.polsek == polsek
            )
            counter = counter.join(
                Location, Location.location_id == CitizenReport.location_id
            ).where(Location.polsek == polsek)

        # Kategori mendesak (tawuran, begal — 9 Oktober 2026) didahulukan di contoh isi dan
        # dihitung terpisah supaya layar dapat menyorotnya; daftarnya satu sumber di taksonomi.
        urgent_categories = load_urgent_categories()
        reports = session.scalars(
            query.order_by(
                CitizenReport.category.in_(urgent_categories).desc(),
                CitizenReport.reported_at.desc(),
            ).limit(SAMPLE_LIMIT)
        ).all()
        urgent_total = int(
            session.scalar(counter.where(CitizenReport.category.in_(urgent_categories))) or 0
        )
        groups.append(
            {
                "kind": "CITIZEN_REPORT",
                "title": "Laporan warga belum diverifikasi",
                "action": "Triase",
                "href": "/ops/masyarakat?status=RECEIVED",
                "total": int(session.scalar(counter) or 0),
                "urgent": urgent_total > 0,
                "urgent_total": urgent_total,
                "items": [
                    {
                        "code": report.code,
                        "headline": report.category,
                        "detail": (report.description or "")[:70] or "Tanpa keterangan.",
                        "urgent": report.category in urgent_categories,
                    }
                    for report in reports
                ],
            }
        )

    # --- Survey Rasa Aman: ulasan menunggu moderasi (2 November 2026) ------------------
    if _holds(current, "review:moderate"):
        pending_reviews = session.scalars(
            select(AreaReview)
            .where(AreaReview.status == "PENDING")
            .order_by(AreaReview.submitted_at.asc())
            .limit(SAMPLE_LIMIT)
        ).all()
        pending_reviews_total = session.scalar(
            select(func.count()).select_from(AreaReview).where(AreaReview.status == "PENDING")
        )
        groups.append(
            {
                "kind": "REVIEW",
                "title": "Ulasan warga menunggu moderasi",
                "action": "Tayangkan atau tolak",
                "href": "/ops/survey",
                "total": int(pending_reviews_total or 0),
                "items": [
                    {
                        "code": review.code,
                        "headline": f"{review.location.kelurahan} · {review.rating}/5",
                        "detail": (review.comment or "")[:70] or "Tanpa komentar.",
                    }
                    for review in pending_reviews
                ],
            }
        )

    # Kelompok kosong tetap dikembalikan, tidak dibuang: "0 peringatan menunggu" adalah
    # kabar baik yang pantas terbaca, dan menghilangkan barisnya membuat pengguna tidak
    # dapat membedakan "tidak ada" dari "tidak diperiksa".
    return {
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "role": current.permissions.role_name,
        "total": sum(int(group["total"]) for group in groups),
        "groups": groups,
        "basis": NOTIFICATION_BASIS,
    }
