"""Kontak Babinkamtibmas DUMMY per kelurahan (2 November 2026, keputusan butir 5):
nomor dinas tiruan, nama tiruan berlabel, satu baris per kelurahan. Deterministik dan
idempoten; baris yang sudah ada (termasuk yang sudah disunting Administrator) tidak disentuh.
"""

from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Babinkamtibmas, Location

SEED = 20261103
RANKS = ("Aipda", "Bripka", "Brigpol", "Aiptu")
GIVEN = (
    "Agus",
    "Budi",
    "Dedi",
    "Eko",
    "Fajar",
    "Hendra",
    "Irwan",
    "Joko",
    "Rudi",
    "Surya",
    "Teguh",
    "Wawan",
)
FAMILY = ("Santoso", "Pratama", "Saputra", "Wijaya", "Nugroho", "Setiawan", "Hidayat", "Kurniawan")


def seed_dummy_babin(session: Session) -> int:
    rng = random.Random(SEED)  # noqa: S311 — data peragaan
    rows = session.execute(
        select(Location.kelurahan, Location.kecamatan, Location.polsek)
        .where(Location.kelurahan.is_not(None))
        .group_by(Location.kelurahan, Location.kecamatan, Location.polsek)
        .order_by(Location.kelurahan)
    ).all()
    existing = set(session.scalars(select(Babinkamtibmas.kelurahan)).all())
    added = 0
    for kelurahan, kecamatan, polsek in rows:
        rank = rng.choice(RANKS)
        name = f"{rng.choice(GIVEN)} {rng.choice(FAMILY)}"
        phone = f"0812-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"
        if kelurahan in existing:
            continue
        session.add(
            Babinkamtibmas(
                kelurahan=str(kelurahan),
                kecamatan=str(kecamatan),
                polsek=str(polsek),
                rank=rank,
                name=f"{name} (dummy)",
                phone_display=phone,
                is_dummy=True,
            )
        )
        added += 1
    session.flush()
    return added
