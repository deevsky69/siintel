"""Model ORM PREDIKSI PRESISI.

Tabel inti (TASK 011) dan tabel publik (TASK 012).
Tabel analitik, operasional, dan administrasi menyusul pada TASK 013–015
mengikuti `docs/02-data-dictionary.md`.

Modul ini diimpor oleh `database/migrations/env.py` supaya seluruh tabel
terdaftar pada `Base.metadata` saat Alembic membandingkan schema.
"""

from .citizen_report import CitizenReport
from .community_feedback import CommunityFeedback
from .crime_incident import CrimeIncident
from .intelligence_report import IntelligenceReport
from .location import Location
from .patrol_activity import PatrolActivity
from .police_unit import PoliceUnit
from .public_alert import PublicAlert

__all__ = [
    "CitizenReport",
    "CommunityFeedback",
    "CrimeIncident",
    "IntelligenceReport",
    "Location",
    "PatrolActivity",
    "PoliceUnit",
    "PublicAlert",
]
