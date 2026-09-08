"""Integration test terhadap PostgreSQL + PostGIS sungguhan.

Dilewati otomatis bila `DATABASE_URL` tidak diisi, sehingga `pytest` tetap hijau
di mesin tanpa database. Di CI, service PostGIS disediakan sehingga test ini benar-benar jalan.

Tujuannya menutup celah yang ditemukan pada TASK 010–011: migration sempat hanya
diverifikasi lewat render SQL, tanpa pernah menyentuh database nyata.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import DatabaseError

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)

CORE_TABLES = {
    "locations",
    "police_units",
    "crime_incidents",
    "intelligence_reports",
    "patrol_activity",
    "citizen_reports",
    "public_alerts",
    "community_feedback",
    "roles",
    "users",
    "permissions",
    "role_permissions",
    "audit_logs",
    "risk_scores",
    "predictions",
    "early_warnings",
    "recommendations",
    "commander_decisions",
    "operational_actions",
    "prediction_actual",
}

_ORIGINAL_RECOMMENDATION = "Usulan asli sistem: penguatan patroli preventif."

_SAMPLE_RECOMMENDATION = text("""
    INSERT INTO recommendations
        (code, prediction_id, recommended_function, recommendation_text, priority, status)
    VALUES
        ('REC-OPS', :prediction_id, 'SAMAPTA', :text, 'MEDIUM', 'PENDING_REVIEW')
    RETURNING recommendation_id
""")

_SAMPLE_USER = text("""
    WITH new_role AS (
        INSERT INTO roles (code, role_name, level) VALUES ('ROLE-OPS', 'Pimpinan Uji', 1)
        RETURNING role_id
    )
    INSERT INTO users (code, username, password_hash, role_id, status)
    SELECT 'USER-OPS', 'uji.pimpinan', 'argon2-hash-uji', role_id, 'ACTIVE' FROM new_role
    RETURNING user_id
""")

_SAMPLE_UNIT = text("""
    INSERT INTO police_units (code, function, unit_name, jurisdiction, status)
    VALUES ('UNIT-OPS', 'SAMAPTA', 'Unit Uji', 'Polsek Tebet', 'ACTIVE')
    RETURNING unit_id
""")

_SAMPLE_PREDICTION = text("""
    INSERT INTO predictions
        (code, prediction_date, forecast_horizon, threat_type, location_id,
         window_start, window_end, risk_score, confidence, dominant_factors,
         model_version, status)
    VALUES
        ('PRD-IT', current_date, '24H', 'CURANMOR', :location_id,
         now(), now() + interval '6 hours', 76, 75,
         '[{"factor": "historical_hotspot", "contribution": 0.4, "source": "RULE"}]'::jsonb,
         'dummy-v1', 'PUBLISHED')
    RETURNING prediction_id
""")

_SAMPLE_WARNING = text("""
    INSERT INTO early_warnings
        (code, prediction_id, severity, threat_type, location_id,
         window_start, window_end, risk_score, status)
    VALUES
        ('WRN-IT', :prediction_id, 'WARNING', 'CURANMOR', :location_id,
         now(), now() + interval '6 hours', 76, 'ACTIVE')
    RETURNING warning_id
""")

_SAMPLE_ROLE = text("""
    INSERT INTO roles (code, role_name, level) VALUES ('ROLE-IT', 'Uji Integrasi', 3)
    RETURNING role_id
""")

_SAMPLE_REPORT = text("""
    INSERT INTO citizen_reports
        (code, reported_at, category, latitude, longitude, geom, status)
    VALUES
        ('RPT-IT', now(), 'Kerawanan Lingkungan', -6.226806, 106.798560,
         ST_SetSRID(ST_MakePoint(106.798560, -6.226806), 4326), 'RECEIVED')
    RETURNING report_id
""")

_SAMPLE_LOCATION = text("""
    INSERT INTO locations
        (code, grid_id, polsek, kecamatan, kelurahan, grid_size_m, latitude, longitude, geom)
    VALUES
        ('LOC-IT', 'JKS-IT', 'Polsek Tebet', 'Tebet', 'Tebet Timur', 500, -6.230653, 106.855133,
         ST_SetSRID(ST_MakePoint(106.855133, -6.230653), 4326))
    RETURNING location_id
""")


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    created = create_engine(DATABASE_URL, future=True)
    yield created
    created.dispose()


def test_migrations_are_applied(engine: Engine) -> None:
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    # Angkanya sengaja dipatok, bukan dibaca dari berkas migrasi. Membacanya dari sana
    # membuat test ini selalu lulus — ia akan membandingkan migrasi dengan dirinya sendiri
    # alih-alih dengan basis data yang benar-benar dipakai.
    assert revision == "0008", "database belum di-migrate: jalankan `pnpm db:migrate`"


def test_postgis_and_pgcrypto_are_installed(engine: Engine) -> None:
    with engine.connect() as connection:
        extensions = set(
            connection.scalars(text("SELECT extname FROM pg_extension")).all(),
        )

    assert {"postgis", "pgcrypto"} <= extensions


def test_core_tables_exist(engine: Engine) -> None:
    with engine.connect() as connection:
        tables = set(
            connection.scalars(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).all()
        )

    assert tables >= CORE_TABLES


def test_geometry_column_is_point_4326(engine: Engine) -> None:
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT type, srid FROM geometry_columns
                WHERE f_table_name = 'locations' AND f_geometry_column = 'geom'
            """)
        ).one()

    assert row.type == "POINT"
    assert row.srid == 4326


def test_uuid_default_and_spatial_query(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        assert location_id is not None, "gen_random_uuid() tidak menghasilkan primary key"

        distance = connection.execute(
            text("""
                SELECT round(ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(106.8552, -6.2307), 4326)::geography
                )::numeric, 1)
                FROM locations WHERE code = 'LOC-IT'
            """)
        ).scalar_one()
        assert distance < 100

        connection.rollback()


def test_foreign_key_restrict_is_enforced(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        connection.execute(
            text("""
                INSERT INTO crime_incidents
                    (code, incident_type, occurred_at, incident_date, incident_time, location_id)
                VALUES
                    ('INC-IT', 'CURANMOR', now(), current_date, '13:51', :location_id)
            """),
            {"location_id": location_id},
        )

        with pytest.raises(DatabaseError):
            connection.execute(text("DELETE FROM locations WHERE code = 'LOC-IT'"))

        connection.rollback()


def test_citizen_report_can_be_created_without_location(engine: Engine) -> None:
    # Laporan masuk dengan koordinat bebas; location_id baru diisi setelah geo-processing.
    with engine.begin() as connection:
        report_id = connection.execute(_SAMPLE_REPORT).scalar_one()

        assert report_id is not None
        location_id = connection.execute(
            text("SELECT location_id FROM citizen_reports WHERE code = 'RPT-IT'")
        ).scalar_one()
        assert location_id is None

        connection.rollback()


def test_community_feedback_requires_existing_report(engine: Engine) -> None:
    with engine.begin() as connection:
        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO community_feedback
                        (code, report_id, feedback_type, submitted_at, status)
                    VALUES
                        ('FDB-IT', gen_random_uuid(), 'Koreksi', now(), 'NEW')
                """)
            )

        connection.rollback()


def test_public_alert_window_order_is_enforced(engine: Engine) -> None:
    with engine.begin() as connection:
        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO public_alerts
                        (code, severity, threat_type, area_text, window_start, window_end,
                         status, public_message)
                    VALUES
                        ('PAL-IT', 'WARNING', 'CURAT', 'Kebayoran Baru',
                         now(), now() - interval '1 hour', 'ACTIVE', 'Imbauan uji')
                """)
            )

        connection.rollback()


def test_intelligence_chain_can_be_created_end_to_end(engine: Engine) -> None:
    """Prediction → early warning → recommendation → public alert, seperti docs/04."""
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        prediction_id = connection.execute(
            _SAMPLE_PREDICTION, {"location_id": location_id}
        ).scalar_one()
        warning_id = connection.execute(
            _SAMPLE_WARNING, {"prediction_id": prediction_id, "location_id": location_id}
        ).scalar_one()
        connection.execute(
            text("""
                INSERT INTO recommendations
                    (code, prediction_id, warning_id, recommended_function,
                     recommendation_text, priority, status)
                VALUES
                    ('REC-IT', :prediction_id, :warning_id, 'SAMAPTA',
                     'Pertimbangkan penguatan kegiatan preventif.', 'MEDIUM', 'PENDING_REVIEW')
            """),
            {"prediction_id": prediction_id, "warning_id": warning_id},
        )
        connection.execute(
            text("""
                INSERT INTO public_alerts
                    (code, warning_id, severity, threat_type, area_text, status, public_message)
                VALUES
                    ('PAL-IT2', :warning_id, 'WARNING', 'CURANMOR', 'Kebayoran Baru',
                     'ACTIVE', 'Imbauan kewaspadaan umum.')
            """),
            {"warning_id": warning_id},
        )

        linked = connection.execute(
            text("""
                SELECT p.code, w.code, r.code, a.code
                FROM predictions p
                JOIN early_warnings w ON w.prediction_id = p.prediction_id
                JOIN recommendations r ON r.warning_id = w.warning_id
                JOIN public_alerts a ON a.warning_id = w.warning_id
                WHERE p.code = 'PRD-IT'
            """)
        ).one()
        assert linked == ("PRD-IT", "WRN-IT", "REC-IT", "PAL-IT2")

        connection.rollback()


def test_public_alert_cannot_reference_unknown_warning(engine: Engine) -> None:
    # Utang FK dari TASK 012 sudah dilunasi pada migration 0005.
    with engine.begin() as connection:
        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO public_alerts
                        (code, warning_id, severity, threat_type, area_text,
                         status, public_message)
                    VALUES
                        ('PAL-IT3', gen_random_uuid(), 'WARNING', 'CURAT', 'Tebet',
                         'ACTIVE', 'Imbauan uji')
                """)
            )

        connection.rollback()


def test_unknown_forecast_horizon_is_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO predictions
                        (code, prediction_date, forecast_horizon, threat_type, location_id,
                         window_start, window_end, risk_score, confidence, dominant_factors,
                         model_version, status)
                    VALUES
                        ('PRD-IT2', current_date, '48H', 'CURAT', :location_id,
                         now(), now() + interval '6 hours', 50, 50, '[]'::jsonb,
                         'dummy-v1', 'DRAFT')
                """),
                {"location_id": location_id},
            )

        connection.rollback()


def test_prediction_without_explanation_is_rejected(engine: Engine) -> None:
    # CLAUDE.md §27: prediksi tanpa WHY tidak boleh tersimpan.
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO predictions
                        (code, prediction_date, forecast_horizon, threat_type, location_id,
                         window_start, window_end, risk_score, confidence,
                         model_version, status)
                    VALUES
                        ('PRD-IT3', current_date, '24H', 'CURAT', :location_id,
                         now(), now() + interval '6 hours', 50, 50, 'dummy-v1', 'DRAFT')
                """),
                {"location_id": location_id},
            )

        connection.rollback()


def test_acknowledging_a_warning_requires_an_actor(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        prediction_id = connection.execute(
            _SAMPLE_PREDICTION, {"location_id": location_id}
        ).scalar_one()
        connection.execute(
            _SAMPLE_WARNING, {"prediction_id": prediction_id, "location_id": location_id}
        )

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    UPDATE early_warnings
                    SET status = 'ACKNOWLEDGED', acknowledged_at = now()
                    WHERE code = 'WRN-IT'
                """)
            )

        connection.rollback()


def _decision_chain(connection: Connection, decision: str, modified_text: str | None = None) -> str:
    """Menyiapkan location → prediction → recommendation → user → keputusan komandan."""
    location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
    prediction_id = connection.execute(
        _SAMPLE_PREDICTION, {"location_id": location_id}
    ).scalar_one()
    recommendation_id = connection.execute(
        _SAMPLE_RECOMMENDATION,
        {"prediction_id": prediction_id, "text": _ORIGINAL_RECOMMENDATION},
    ).scalar_one()
    user_id = connection.execute(_SAMPLE_USER).scalar_one()

    decision_id = connection.execute(
        text("""
            INSERT INTO commander_decisions
                (code, recommendation_id, decision_by, decision, reason, modified_text)
            VALUES
                ('DEC-OPS', :recommendation_id, :user_id, :decision, 'alasan uji', :modified_text)
            RETURNING decision_id
        """),
        {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "decision": decision,
            "modified_text": modified_text,
        },
    ).scalar_one()
    return str(decision_id)


def _insert_action(connection: Connection, decision_id: str) -> None:
    location_id = connection.execute(
        text("SELECT location_id FROM locations WHERE code = 'LOC-IT'")
    ).scalar_one()
    unit_id = connection.execute(_SAMPLE_UNIT).scalar_one()
    connection.execute(
        text("""
            INSERT INTO operational_actions
                (code, decision_id, unit_id, location_id, start_at, status)
            VALUES
                ('ACT-OPS', :decision_id, :unit_id, :location_id, now(), 'PLANNED')
        """),
        {"decision_id": decision_id, "unit_id": unit_id, "location_id": location_id},
    )


def test_action_can_be_created_from_an_approved_decision(engine: Engine) -> None:
    with engine.begin() as connection:
        decision_id = _decision_chain(connection, "APPROVED")

        _insert_action(connection, decision_id)

        status = connection.execute(
            text("SELECT status FROM operational_actions WHERE code = 'ACT-OPS'")
        ).scalar_one()
        assert status == "PLANNED"

        connection.rollback()


def test_action_cannot_be_created_from_a_rejected_decision(engine: Engine) -> None:
    """Invarian inti produk: AI tidak pernah langsung memerintahkan tindakan."""
    with engine.begin() as connection:
        decision_id = _decision_chain(connection, "REJECTED")

        with pytest.raises(DatabaseError):
            _insert_action(connection, decision_id)

        connection.rollback()


def test_modified_decision_requires_new_text(engine: Engine) -> None:
    with engine.begin() as connection:
        with pytest.raises(DatabaseError):
            _decision_chain(connection, "MODIFIED", modified_text=None)

        connection.rollback()


def test_modified_decision_preserves_the_original_recommendation(engine: Engine) -> None:
    """Jejak usulan AI dan keputusan manusia harus keduanya utuh (U-07)."""
    with engine.begin() as connection:
        _decision_chain(connection, "MODIFIED", modified_text="Versi komandan: tambah 1 unit.")

        original, modified = connection.execute(
            text("""
                SELECT r.recommendation_text, d.modified_text
                FROM recommendations r
                JOIN commander_decisions d ON d.recommendation_id = r.recommendation_id
                WHERE r.code = 'REC-OPS'
            """)
        ).one()

        assert original == _ORIGINAL_RECOMMENDATION
        assert modified == "Versi komandan: tambah 1 unit."

        connection.rollback()


def test_false_negative_can_be_recorded_without_a_prediction(engine: Engine) -> None:
    """Tanpa ini recall tidak dapat dihitung (CLAUDE.md §26)."""
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        incident_id = connection.execute(
            text("""
                INSERT INTO crime_incidents
                    (code, incident_type, occurred_at, incident_date, incident_time, location_id)
                VALUES
                    ('INC-FN', 'CURANMOR', now(), current_date, '02:15', :location_id)
                RETURNING incident_id
            """),
            {"location_id": location_id},
        ).scalar_one()

        connection.execute(
            text("""
                INSERT INTO prediction_actual
                    (code, evaluation_date, actual_incident_id, actual_event, match_type)
                VALUES
                    ('EVA-FN', current_date, :incident_id, true, 'FALSE_NEGATIVE')
            """),
            {"incident_id": incident_id},
        )

        prediction_id = connection.execute(
            text("SELECT prediction_id FROM prediction_actual WHERE code = 'EVA-FN'")
        ).scalar_one()
        assert prediction_id is None

        connection.rollback()


def test_hit_without_prediction_is_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO prediction_actual
                        (code, evaluation_date, actual_event, match_type)
                    VALUES
                        ('EVA-BAD', current_date, true, 'HIT')
                """)
            )

        connection.rollback()


def test_every_foreign_key_column_is_indexed(engine: Engine) -> None:
    """Aturan TASK 016: kolom FK tanpa index membuat pemeriksaan RESTRICT/CASCADE
    dan jalur join melakukan sequential scan. Test ini menjaga aturan itu untuk tabel baru.
    """
    with engine.connect() as connection:
        unindexed = (
            connection.execute(
                text("""
                SELECT c.conrelid::regclass::text || '.' || a.attname
                FROM pg_constraint c
                JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                WHERE c.contype = 'f' AND k.ord = 1
                  AND NOT EXISTS (
                      SELECT 1 FROM pg_index i
                      WHERE i.indrelid = c.conrelid AND i.indkey[0] = k.attnum
                  )
                ORDER BY 1
            """)
            )
            .scalars()
            .all()
        )

    assert unindexed == [], f"kolom FK tanpa index: {unindexed}"


def test_every_table_with_updated_at_has_its_trigger(engine: Engine) -> None:
    """Tanpa trigger, `updated_at` berbohong pada setiap penulisan di luar ORM."""
    with engine.connect() as connection:
        missing = (
            connection.execute(
                text("""
                SELECT c.table_name
                FROM information_schema.columns c
                WHERE c.table_schema = 'public' AND c.column_name = 'updated_at'
                  AND NOT EXISTS (
                      SELECT 1 FROM pg_trigger t
                      WHERE t.tgrelid = c.table_name::regclass
                        AND t.tgname = 'trg_' || c.table_name || '_set_updated_at'
                  )
                ORDER BY 1
            """)
            )
            .scalars()
            .all()
        )

    assert missing == [], f"tabel tanpa trigger updated_at: {missing}"


def test_updated_at_is_refreshed_by_plain_sql_update(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO locations
                    (code, grid_id, polsek, kecamatan, grid_size_m, latitude, longitude,
                     geom, updated_at)
                VALUES
                    ('LOC-UPD', 'JKS-UPD', 'Polsek Tebet', 'Tebet', 500, -6.23, 106.85,
                     ST_SetSRID(ST_MakePoint(106.85, -6.23), 4326),
                     timestamptz '2020-01-01 00:00+07')
            """)
        )
        connection.execute(
            text("UPDATE locations SET kecamatan = 'Tebet Baru' WHERE code = 'LOC-UPD'")
        )

        refreshed = connection.execute(
            text("""
                SELECT updated_at > timestamptz '2020-01-02'
                FROM locations WHERE code = 'LOC-UPD'
            """)
        ).scalar_one()
        assert refreshed is True

        connection.rollback()


def test_impossible_coordinates_are_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO locations
                        (code, grid_id, polsek, kecamatan, grid_size_m, latitude, longitude, geom)
                    VALUES
                        ('LOC-BAD', 'JKS-BAD', 'Polsek Tebet', 'Tebet', 500, 999, -999,
                         ST_SetSRID(ST_MakePoint(106.85, -6.23), 4326))
                """)
            )

        connection.rollback()


def test_revoking_a_role_removes_its_permission_grants(engine: Engine) -> None:
    with engine.begin() as connection:
        role_id = connection.execute(_SAMPLE_ROLE).scalar_one()
        permission_id = connection.execute(
            text("""
                INSERT INTO permissions (code, resource, action)
                VALUES ('PERM-IT', 'uji_resource', 'read')
                RETURNING permission_id
            """)
        ).scalar_one()
        connection.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id, scope)
                VALUES (:role_id, :permission_id, 'OWN_JURISDICTION')
            """),
            {"role_id": role_id, "permission_id": permission_id},
        )

        connection.execute(text("DELETE FROM roles WHERE code = 'ROLE-IT'"))

        remaining = connection.execute(
            text("SELECT count(*) FROM role_permissions WHERE role_id = :role_id"),
            {"role_id": role_id},
        ).scalar_one()
        assert remaining == 0

        connection.rollback()


def test_invalid_scope_is_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        role_id = connection.execute(_SAMPLE_ROLE).scalar_one()
        permission_id = connection.execute(
            text("""
                INSERT INTO permissions (code, resource, action)
                VALUES ('PERM-IT2', 'uji_resource', 'write')
                RETURNING permission_id
            """)
        ).scalar_one()

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO role_permissions (role_id, permission_id, scope)
                    VALUES (:role_id, :permission_id, 'SEMUA_WILAYAH')
                """),
                {"role_id": role_id, "permission_id": permission_id},
            )

        connection.rollback()


def test_audit_log_accepts_denied_and_rejects_unknown_result(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO audit_logs (action, resource_type, resource_id, result)
                VALUES ('APPROVE_RECOMMENDATION', 'recommendation', 'REC-0001', 'DENIED')
            """)
        )

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO audit_logs (action, resource_type, result)
                    VALUES ('LOGIN', 'auth', 'BERHASIL')
                """)
            )

        connection.rollback()


def test_audit_log_allows_system_events_without_user(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO audit_logs (action, resource_type, result)
                VALUES ('IMPORT_DATA', 'crime', 'SUCCESS')
            """)
        )

        user_id = connection.execute(
            text("SELECT user_id FROM audit_logs WHERE action = 'IMPORT_DATA'")
        ).scalar_one()
        assert user_id is None

        connection.rollback()


def test_score_check_constraint_is_enforced(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO intelligence_reports
                        (code, report_date, category, location_id, confidence)
                    VALUES
                        ('INT-IT', current_date, 'Potensi Tawuran', :location_id, 150)
                """),
                {"location_id": location_id},
            )

        connection.rollback()
