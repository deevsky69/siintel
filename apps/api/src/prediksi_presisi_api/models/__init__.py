"""Model ORM PREDIKSI PRESISI.

Urutan pembuatan tabel (lihat `docs/08` PHASE 2):

- TASK 011 — inti: locations, police_units, crime_incidents, intelligence_reports, patrol_activity
- TASK 012 — publik: citizen_reports, public_alerts, community_feedback
- TASK 015 — administrasi: roles, users, permissions, role_permissions, audit_logs
- TASK 013 — intelijen: risk_scores, predictions, early_warnings, recommendations
  (sekaligus memasang FK public_alerts.warning_id yang tertunda dari TASK 012)
- TASK 014 — operasional: commander_decisions, operational_actions, prediction_actual

Modul ini diimpor oleh `database/migrations/env.py` supaya seluruh tabel
terdaftar pada `Base.metadata` saat Alembic membandingkan schema.
"""

from .audit_log import AuditLog
from .citizen_report import CitizenReport
from .commander_decision import CommanderDecision
from .community_feedback import CommunityFeedback
from .crime_incident import CrimeIncident
from .early_warning import EarlyWarning
from .intelligence_report import IntelligenceReport
from .location import Location
from .operational_action import OperationalAction
from .patrol_activity import PatrolActivity
from .police_unit import PoliceUnit
from .prediction import Prediction
from .prediction_actual import PredictionActual
from .public_alert import PublicAlert
from .rbac import Permission, Role, RolePermission, User
from .recommendation import Recommendation
from .risk_score import RiskScore

__all__ = [
    "AuditLog",
    "CitizenReport",
    "CommanderDecision",
    "CommunityFeedback",
    "CrimeIncident",
    "EarlyWarning",
    "IntelligenceReport",
    "Location",
    "OperationalAction",
    "PatrolActivity",
    "Permission",
    "PoliceUnit",
    "Prediction",
    "PredictionActual",
    "PublicAlert",
    "Recommendation",
    "RiskScore",
    "Role",
    "RolePermission",
    "User",
]
