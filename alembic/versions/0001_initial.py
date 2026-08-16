"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

from app.models import GUID

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "project_members",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "editor", "viewer", name="roleenum"),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("todo", "in_progress", "done", name="statusenum"),
            nullable=False,
        ),
        sa.Column("assignee_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tasks")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
