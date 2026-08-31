"""Model ORM PREDIKSI PRESISI.

Tabel inti (TASK 011). Tabel publik, analitik, operasional, dan administrasi
menyusul pada TASK 012–015 mengikuti `docs/02-data-dictionary.md`.

Modul ini diimpor oleh `database/migrations/env.py` supaya seluruh tabel
terdaftar pada `Base.metadata` saat Alembic membandingkan schema.
"""

from .crime_incident import CrimeIncident
from .intelligence_report import IntelligenceReport
from .location import Location
from .patrol_activity import PatrolActivity
from .police_unit import PoliceUnit

__all__ = [
    "CrimeIncident",
    "IntelligenceReport",
    "Location",
    "PatrolActivity",
    "PoliceUnit",
]
