import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Date, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR

from .database import Base


class GUID(TypeDecorator):
    """Platform-independent UUID column.

    Uses Postgres' native UUID type when the dialect is postgres, and falls
    back to a CHAR(36) string on SQLite (used for local dev/tests) so the
    same models work against both databases without changes.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


def gen_uuid() -> uuid.UUID:
    return uuid.uuid4()


class RoleEnum(str, enum.Enum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class StatusEnum(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owned_projects = relationship("Project", back_populates="owner")
    memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.viewer)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="memberships")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(StatusEnum), nullable=False, default=StatusEnum.todo)
    assignee_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
