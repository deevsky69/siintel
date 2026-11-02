"""Berkas perkara DUMMY untuk peragaan lacak laporan dan cek kendaraan (2 November 2026).

Deterministik (seed tetap) supaya nomor LP dan PIN yang sama muncul di setiap lingkungan;
idempoten (nomor LP sudah ada → dilewati). Setiap baris `is_dummy = true` dan menyimpan
`dummy_pin` agar PIN-nya dapat ditampilkan di layar petugas — TIDAK berlaku untuk perkara
sungguhan, yang PIN-nya hanya di tangan pelapor.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CaseFile, CaseStage, Location
from ..models.case_file import CRIME_TYPES, STAGES, hash_pin, normalize_plate
from ..services import clock

SEED = 20261102
COUNT = 48
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
MOTORS = (
    "Honda Vario 150 hitam", "Yamaha NMAX putih", "Honda Beat merah", "Honda Scoopy biru",
    "Yamaha Mio hijau", "Honda PCX abu-abu", "Suzuki Satria hitam", "Yamaha Aerox kuning",
)  # fmt: skip
SUMMARIES = {
    "CURANMOR": "Kendaraan hilang saat diparkir; pelapor menyerahkan STNK dan kunci.",
    "CURAT": "Rumah dimasuki saat kosong; barang elektronik dan perhiasan hilang.",
    "CURAS": "Pelapor dirampas tasnya oleh dua orang bersepeda motor.",
}
STAGE_NOTES = {
    "DITERIMA": "Laporan diterima SPKT; pelapor menerima STPL.",
    "LIDIK": "Penyelidikan: pemeriksaan saksi dan rekaman CCTV sekitar.",
    "SIDIK": "Penyidikan: tersangka teridentifikasi; SP2HP dikirim ke pelapor.",
    "P21": "Berkas dinyatakan lengkap oleh JPU.",
    "SP3": "Penyidikan dihentikan karena bukti tidak cukup; SP2HP dikirim.",
    "SELESAI": "Perkara selesai; barang bukti dikembalikan.",
}


@dataclass(frozen=True)
class DummyCase:
    lp_number: str
    pin: str
    crime_type: str
    kelurahan: str | None
    stage: str
    plate: str | None


def _plate(rng: random.Random) -> str:
    letters = "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(3))
    return f"B {rng.randint(1000, 9999)} {letters}"


def _vin(rng: random.Random) -> str:
    return "MH1" + "".join(rng.choice("0123456789ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(14))


def seed_dummy_case_files(session: Session, reference: date | None = None) -> list[DummyCase]:
    """Menanam COUNT berkas dummy; mengembalikan daftar (LP, PIN) untuk dicatat di peragaan."""
    rng = random.Random(SEED)  # noqa: S311 — data peragaan, bukan kriptografi
    today = reference or clock.reference_now().astimezone(clock.JAKARTA).date()
    locations = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    ).all()
    if not locations:
        return []
    existing = set(session.scalars(select(CaseFile.lp_number)).all())
    made: list[DummyCase] = []
    sequence = 100
    for _ in range(COUNT):
        location = rng.choice(locations)
        crime = rng.choices(CRIME_TYPES, weights=(5, 4, 1))[0]
        reported = today - timedelta(days=rng.randint(3, 150))
        sequence += rng.randint(1, 9)
        unit = str(location.polsek).upper()
        unit = unit if unit.startswith("POLSEK") else f"POLSEK {unit}"
        lp_number = f"LP/B/{sequence}/{ROMAN[reported.month - 1]}/{reported.year}/SPKT/{unit}"
        pin = f"{rng.randint(0, 9999):04d}"
        # Tahap maju sebanding umur laporan; SP3 dan SELESAI hanya untuk yang lama.
        age = (today - reported).days
        choices = STAGES[: 2 if age < 20 else 3 if age < 60 else 6]
        stage = rng.choice(choices)
        plate = _plate(rng) if crime == "CURANMOR" else None
        # Seluruh nilai acak ditarik SEBELUM pemeriksaan "sudah ada", supaya urutan rng — dan
        # karenanya nomor LP serta PIN — sama persis pada setiap pemanggilan ulang.
        vin = _vin(rng) if plate else None
        engine = f"JF{rng.randint(10, 99)}E{rng.randint(1000000, 9999999)}" if plate else None
        motor = rng.choice(MOTORS) if plate else None
        gaps = [rng.randint(2, 14) for _ in STAGES]
        made.append(DummyCase(lp_number, pin, crime, location.kelurahan, stage, plate))
        if lp_number in existing:
            continue
        existing.add(lp_number)
        history: list[CaseStage] = []
        at = datetime.combine(reported, time(9, 0), tzinfo=clock.JAKARTA)
        for index, step in enumerate(STAGES[: STAGES.index(stage) + 1]):
            if step in ("P21", "SP3") and step != stage:
                continue
            history.append(CaseStage(stage=step, changed_at=at, note=STAGE_NOTES[step]))
            at = at + timedelta(days=gaps[index])
        session.add(
            CaseFile(
                lp_number=lp_number,
                crime_type=crime,
                location_id=location.location_id,
                reported_on=reported,
                stage=stage,
                stage_updated_at=history[-1].changed_at if history else at,
                summary=SUMMARIES[crime],
                vehicle_plate=normalize_plate(plate) if plate else None,
                vehicle_plate_display=plate,
                vehicle_vin=vin,
                vehicle_engine=engine,
                vehicle_desc=motor,
                vehicle_recovered=plate is not None and stage == "SELESAI",
                reporter_pin_hash=hash_pin(lp_number, pin),
                is_dummy=True,
                dummy_pin=pin,
                stages=history,
            )
        )
    session.flush()
    return made
