"""Survey Rasa Aman — `area_reviews` + permission `review:moderate` (Administrator).

Keputusan pemilik proyek 2 November 2026: ulasan warga per kelurahan, anonim, moderasi dulu
baru tayang. Lihat `models/area_review.py`.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "area_reviews",
        sa.Column(
            "review_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("moderated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderation_note", sa.String(300), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("review_id", name="pk_area_reviews"),
        sa.UniqueConstraint("code", name="uq_area_reviews_code"),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_area_reviews_location_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["moderated_by"],
            ["users.user_id"],
            name="fk_area_reviews_moderated_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="review_rating_range"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PUBLISHED', 'REJECTED')", name="review_status_allowed"
        ),
    )
    op.create_index("ix_area_reviews_location_status", "area_reviews", ["location_id", "status"])
    op.create_index("ix_area_reviews_status_submitted", "area_reviews", ["status", "submitted_at"])
    op.create_index("ix_area_reviews_moderated_by", "area_reviews", ["moderated_by"])
    op.execute(
        "CREATE TRIGGER trg_area_reviews_set_updated_at BEFORE UPDATE ON "
        "area_reviews FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    if context.is_offline_mode():
        return
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT 1 FROM permissions WHERE resource = 'review' AND action = 'moderate'")
    ).first()
    if not exists:
        nxt = bind.execute(
            sa.text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 6) AS INTEGER)), 0) + 1 "
                "FROM permissions WHERE code LIKE 'PERM-%'"
            )
        ).scalar_one()
        bind.execute(
            sa.text(
                "INSERT INTO permissions (permission_id, code, resource, action, description, "
                "created_at, updated_at) VALUES (gen_random_uuid(), :code, 'review', 'moderate', "
                "'Memoderasi ulasan Survey Rasa Aman', now(), now())"
            ),
            {"code": f"PERM-{int(nxt):03d}"},
        )
    bind.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id, scope) "
            "SELECT r.role_id, p.permission_id, 'ALL' FROM roles r, permissions p "
            "WHERE r.role_name = 'Administrator' AND p.resource = 'review' AND p.action = 'moderate' "
            "AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.role_id "
            "AND rp.permission_id = p.permission_id)"
        )
    )


def downgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        bind.execute(
            sa.text(
                "DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id = "
                "p.permission_id AND p.resource = 'review' AND p.action = 'moderate'"
            )
        )
        bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'review'"))
    op.execute("DROP TRIGGER IF EXISTS trg_area_reviews_set_updated_at ON area_reviews")
    op.execute("DROP INDEX IF EXISTS ix_area_reviews_moderated_by")
    op.execute("DROP INDEX IF EXISTS ix_area_reviews_status_submitted")
    op.execute("DROP INDEX IF EXISTS ix_area_reviews_location_status")
    op.drop_table("area_reviews")
