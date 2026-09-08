"""Penyimpanan lampiran laporan masyarakat.

Modul ini memikul satu janji yang dibuat kepada pelapor: **metadata berkas dilucuti**.
Foto dari ponsel hampir selalu membawa EXIF berisi koordinat GPS, merek dan nomor seri
kamera, serta waktu pengambilan. Pelapor yang mengira dirinya anonim karena tidak mengetik
namanya akan tetap dikenali dari itu.

TIGA LAPIS PEMERIKSAAN, DAN MENGAPA KETIGANYA PERLU

1. **Ukuran.** Diperiksa saat mengalir, bukan setelah berkasnya utuh di memori. Kanal ini
   terbuka tanpa akun; menerima dulu lalu menolak berarti siapa pun dapat memaksa server
   menampung berkas sebesar apa pun.

2. **Jenis berkas dari ISINYA, bukan dari klaim pengirim.** `Content-Type` dan nama berkas
   dikirim klien dan dapat ditulis apa saja. Yang diperiksa di sini adalah tanda tangan
   byte pertama.

3. **Pelucutan metadata.** Gambar dibuka lalu ditulis ulang tanpa EXIF; suara dan video
   di-remux tanpa metadata. Ringkasan `sha256` diambil dari hasilnya — dari berkas yang
   benar-benar tersimpan, bukan dari yang diunggah.

BERKAS DISIMPAN DI CAKRAM, BUKAN DI BASIS DATA

    Bukan karena ukuran, melainkan karena penghapusan. Masa retensi menuntut berkas
    benar-benar hilang; kolom `bytea` yang di-`UPDATE` menjadi NULL meninggalkan salinannya
    di WAL dan di cadangan sampai entah kapan.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CitizenReport, CitizenReportAttachment

#: Batas ukuran satu lampiran. Cukup untuk foto ponsel dan rekaman pendek; tidak cukup
#: untuk menjadikan kanal publik tempat menitipkan berkas.
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024

#: Berapa banyak lampiran yang boleh menyertai satu laporan.
MAX_ATTACHMENTS_PER_REPORT = 3

#: Berapa lama sebuah unggahan menunggu laporannya. Handle yang tidak pernah dipakai
#: dibersihkan setelah ini — kalau tidak, kanal publik menjadi tempat penitipan berkas.
STAGING_TTL_MINUTES = 30

#: Masa retensi lampiran setelah laporannya selesai. Keputusan pemilik proyek 8 Sep 2026.
RETENTION_DAYS_AFTER_CLOSED = 90

#: Status laporan yang dianggap selesai — sejak itulah hitungan retensi berjalan.
#:
#: Hanya `CLOSED`. Taksonomi `status_citizen_report` pada `config/taxonomy/mappings.yaml`
#: mengenal lima status (Diterima, Diverifikasi, Diteruskan, Ditangani, Selesai) dan hanya
#: yang terakhir berarti selesai. Menambahkan status yang tidak ada di taksonomi — "REJECTED",
#: "ARCHIVED" — berarti mengarang alur kerja yang tidak pernah ditetapkan siapa pun.
CLOSED_STATUS = "CLOSED"

#: Tanda tangan byte pertama, dipetakan ke (jenis, tipe MIME).
#:
#: Diperiksa dari isi berkas karena `Content-Type` dan nama berkas datang dari klien dan
#: dapat ditulis apa saja. Daftar ini sengaja pendek: setiap format tambahan adalah pengurai
#: tambahan yang harus dipercaya menghadapi berkas dari orang tak dikenal.
_SIGNATURES: tuple[tuple[bytes, int, str, str], ...] = (
    (b"\xff\xd8\xff", 0, "IMAGE", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", 0, "IMAGE", "image/png"),
    (b"RIFF", 0, "IMAGE", "image/webp"),  # dipastikan lagi lewat "WEBP" di offset 8
    (b"ftyp", 4, "VIDEO", "video/mp4"),
    (b"\x1a\x45\xdf\xa3", 0, "VIDEO", "video/webm"),
    (b"OggS", 0, "AUDIO", "audio/ogg"),
    (b"ID3", 0, "AUDIO", "audio/mpeg"),
    (b"\xff\xfb", 0, "AUDIO", "audio/mpeg"),
)


#: Bentuk handle yang sah — persis keluaran `secrets.token_urlsafe(32)`.
#:
#: Diperiksa sebelum menyentuh cakram, dan itu bukan kehati-hatian berlebihan. Sebelum
#: pemeriksaan ini ada, handle dipakai langsung sebagai pola `glob`, sehingga mengirim
#: handle `*` akan cocok dengan titipan SIAPA PUN yang sedang menunggu — dan menempelkan
#: berkas orang lain ke laporan sendiri. Rahasia 256 bit tidak menjaga apa-apa bila nilainya
#: diperlakukan sebagai pola, bukan sebagai nama.
_HANDLE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")


class AttachmentError(Exception):
    """Lampiran ditolak. Pesannya ditujukan kepada pelapor, bukan kepada pengembang."""


@dataclass(frozen=True)
class StoredAttachment:
    kind: str
    media_type: str
    byte_size: int
    sha256: str
    storage_key: str
    metadata_stripped_with: str


def storage_root() -> Path:
    """Direktori tempat berkas lampiran disimpan.

    Dibaca dari environment supaya dapat diarahkan ke volume di produksi dan ke direktori
    sementara di dalam test. Nilai bawaannya berada di dalam repositori dan **tidak** ikut
    ke Git — lihat `.gitignore`.
    """
    configured = os.environ.get("ATTACHMENT_DIR")
    root = Path(configured) if configured else Path(__file__).resolve().parents[4] / "var/lampiran"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _staging_root() -> Path:
    root = storage_root() / "_menunggu"
    root.mkdir(parents=True, exist_ok=True)
    return root


def sniff(head: bytes) -> tuple[str, str]:
    """Jenis dan tipe MIME dari byte pertama berkas.

    Melempar [AttachmentError] bila tidak dikenali. Menerima berkas yang tidak dikenali
    lalu "mencoba yang terbaik" berarti menyimpan sesuatu yang tidak seorang pun tahu
    isinya, di kanal yang terbuka bagi siapa saja.
    """
    for signature, offset, kind, media_type in _SIGNATURES:
        if head[offset : offset + len(signature)] != signature:
            continue
        # RIFF dipakai banyak format; hanya WEBP yang diterima di sini.
        if media_type == "image/webp" and head[8:12] != b"WEBP":
            continue
        return kind, media_type
    raise AttachmentError(
        "Jenis berkas tidak dikenali. Yang diterima: foto JPEG/PNG/WebP, "
        "suara MP3/OGG, video MP4/WebM."
    )


def _copy_with_limit(source: BinaryIO, target: BinaryIO, limit: int) -> int:
    """Menyalin sambil menghitung, dan berhenti begitu melewati batas.

    Batasnya diperiksa **saat mengalir**. Membaca seluruh berkas lebih dulu lalu memeriksa
    panjangnya berarti seseorang tanpa akun dapat memaksa server menampung berkas sebesar
    apa pun sebelum ditolak.
    """
    total = 0
    while True:
        chunk = source.read(64 * 1024)
        if not chunk:
            return total
        total += len(chunk)
        if total > limit:
            raise AttachmentError(f"Berkas melebihi batas {limit // (1024 * 1024)} MB.")
        target.write(chunk)


def _strip_image(source: Path, target: Path) -> str:
    """Menulis ulang gambar tanpa metadata apa pun."""
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover — dependensi wajib di produksi
        raise AttachmentError("Pemroses gambar tidak tersedia di server.") from error

    with Image.open(source) as image:
        image.load()
        # Gambar baru yang kosong, lalu pikselnya ditempelkan. `image.copy()` TIDAK dapat
        # dipakai: ia ikut membawa `info`, tempat EXIF, ICC, dan komentar tersimpan — dan
        # hasilnya terlihat seperti gambar yang bersih padahal seluruh metadatanya utuh.
        bare = Image.new(image.mode, image.size)
        bare.paste(image)
        bare.save(target, format=image.format)
    return "pillow"


def _strip_media(source: Path, target: Path, media_type: str) -> str:
    """Menyalin ulang suara/video tanpa metadata, tanpa mengodekan ulang isinya.

    `-map_metadata -1` membuang seluruh metadata wadah, termasuk atom `©xyz` pada MP4 yang
    memuat koordinat GPS. `-c copy` menyalin aliran apa adanya, sehingga prosesnya cepat
    dan mutunya tidak berkurang.
    """
    # Jalur lengkap, bukan nama "ffmpeg" saja: memanggil lewat nama berarti bergantung pada
    # PATH proses, dan PATH dapat berbeda antara shell pengembang dan proses di dalam
    # container.
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise AttachmentError(
            "Server belum dapat memproses berkas suara dan video. Kirim foto, atau "
            "sampaikan keterangannya sebagai tulisan."
        )

    fmt = "mp4" if media_type == "video/mp4" else target.suffix.lstrip(".")
    result = subprocess.run(  # noqa: S603 — argumen tetap, tidak ada masukan pengguna
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(source),
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c",
            "copy",
            "-f",
            fmt,
            str(target),
        ],
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0 or not target.exists() or target.stat().st_size == 0:
        raise AttachmentError("Berkas tidak dapat diproses. Coba kirim ulang dalam format lain.")
    return "ffmpeg"


_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


def stage(upload: BinaryIO, now: datetime) -> tuple[str, StoredAttachment]:
    """Menerima satu unggahan, melucuti metadatanya, dan menyimpannya sebagai titipan.

    Mengembalikan sepasang: **handle** yang harus disertakan saat mengirim laporan, dan
    keterangan berkas yang tersimpan.

    Handle-nya rahasia acak 256 bit, bukan nomor urut. Nomor urut dapat ditebak, dan
    menebaknya akan berarti menempelkan berkas orang lain ke laporan sendiri.
    """
    head = upload.read(16)
    upload.seek(0)
    kind, media_type = sniff(head)
    suffix = _SUFFIX[media_type]

    staging = _staging_root()
    handle = secrets.token_urlsafe(32)

    with tempfile.TemporaryDirectory(dir=staging) as workspace:
        raw = Path(workspace) / f"masuk{suffix}"
        with raw.open("wb") as target:
            _copy_with_limit(upload, target, MAX_ATTACHMENT_BYTES)

        clean = Path(workspace) / f"bersih{suffix}"
        tool = _strip_image(raw, clean) if kind == "IMAGE" else _strip_media(raw, clean, media_type)

        digest = hashlib.sha256()
        with clean.open("rb") as handle_in:
            for chunk in iter(lambda: handle_in.read(64 * 1024), b""):
                digest.update(chunk)

        stored = StoredAttachment(
            kind=kind,
            media_type=media_type,
            byte_size=clean.stat().st_size,
            sha256=digest.hexdigest(),
            storage_key=f"{handle}{suffix}",
            metadata_stripped_with=tool,
        )
        # Dipindahkan setelah seluruh pemeriksaan lulus: berkas yang muncul di direktori
        # titipan berarti berkas yang sudah bersih, tidak pernah yang sedang diproses.
        shutil.move(str(clean), str(staging / stored.storage_key))

    # Tanda dinamai `<handle>.tanda`, bukan `<handle>.<ext>.tanda`. Keduanya sama-sama
    # bekerja saat pencarian memakai pola, tetapi pencarian dengan pola itulah yang
    # membuat handle dapat dipalsukan. Dengan nama yang tepat, batang nama tanda dan berkas
    # isinya sama-sama persis handle-nya.
    (staging / f"{handle}.tanda").write_text(
        f"{now.isoformat()}\n{stored.kind}\n{stored.media_type}\n"
        f"{stored.byte_size}\n{stored.sha256}\n{stored.metadata_stripped_with}\n",
        encoding="utf-8",
    )
    return handle, stored


def claim(handle: str) -> StoredAttachment:
    """Mengambil titipan menjadi lampiran tetap.

    Handle yang tidak dikenal ditolak dengan pesan yang sama seperti handle yang sudah
    kedaluwarsa: membedakan keduanya akan memberi tahu penebak bahwa tebakannya mendekati.
    """
    if not _HANDLE.fullmatch(handle):
        raise AttachmentError("Lampiran tidak ditemukan atau sudah kedaluwarsa.")

    staging = _staging_root()
    marker = staging / f"{handle}.tanda"
    # Pencarian berkas isinya memakai perbandingan nama yang tepat, bukan pola. Sufiksnya
    # bergantung jenis berkas dan tidak diketahui di sini, tetapi batang namanya pasti.
    payload = next(
        (
            path
            for path in staging.iterdir()
            if path.is_file() and path.stem == handle and path.suffix != ".tanda"
        ),
        None,
    )
    if not marker.is_file() or payload is None:
        raise AttachmentError("Lampiran tidak ditemukan atau sudah kedaluwarsa.")

    _, kind, media_type, byte_size, sha256, tool = marker.read_text(encoding="utf-8").split("\n")[
        :6
    ]
    stored = StoredAttachment(
        kind=kind,
        media_type=media_type,
        byte_size=int(byte_size),
        sha256=sha256,
        storage_key=payload.name,
        metadata_stripped_with=tool,
    )

    shutil.move(str(payload), str(storage_root() / stored.storage_key))
    marker.unlink(missing_ok=True)
    return stored


def path_of(attachment: CitizenReportAttachment) -> Path:
    return storage_root() / attachment.storage_key


def sweep_staging(now: datetime) -> int:
    """Membuang titipan yang tidak pernah dipakai. Mengembalikan jumlah yang dibuang."""
    cutoff = now - timedelta(minutes=STAGING_TTL_MINUTES)
    removed = 0
    for marker in _staging_root().glob("*.tanda"):
        stamp = marker.read_text(encoding="utf-8").split("\n")[0]
        try:
            created = datetime.fromisoformat(stamp)
        except ValueError:
            created = cutoff - timedelta(days=1)  # tanda rusak: perlakukan sebagai basi
        if created <= cutoff:
            for sibling in marker.parent.iterdir():
                if sibling.is_file() and sibling.stem == marker.stem:
                    sibling.unlink(missing_ok=True)
            removed += 1
    return removed


def purge_expired(session: Session, now: datetime) -> list[str]:
    """Menghapus berkas lampiran yang sudah lewat masa retensinya.

    Yang dihapus adalah **berkasnya**, bukan barisnya. Jejak bahwa pernah ada lampiran, dan
    kapan ia dimusnahkan, adalah bagian dari pertanggungjawaban — menghapus barisnya berarti
    menghapus juga bukti bahwa penghapusan itu benar-benar dijalankan.

    Hitungan mulai dari saat laporannya **selesai**, bukan dari saat lampirannya diunggah:
    berkas yang masih dibutuhkan pemeriksaan tidak boleh hilang di tengah jalan.
    """
    cutoff = now - timedelta(days=RETENTION_DAYS_AFTER_CLOSED)
    stale = session.scalars(
        select(CitizenReportAttachment)
        .join(CitizenReport)
        .where(
            CitizenReportAttachment.purged_at.is_(None),
            CitizenReport.status == CLOSED_STATUS,
            # `closed_at`, bukan `updated_at`: yang kedua dikelola trigger dan berubah pada
            # setiap penyuntingan, sehingga satu perbaikan ejaan akan memundurkan
            # penghapusan berkasnya tiga bulan lagi tanpa ada yang memutuskannya.
            CitizenReport.closed_at.is_not(None),
            CitizenReport.closed_at <= cutoff,
        )
    ).all()

    purged: list[str] = []
    for attachment in stale:
        path_of(attachment).unlink(missing_ok=True)
        attachment.purged_at = now
        purged.append(str(attachment.attachment_id))
    return purged
