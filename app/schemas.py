import uuid
from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, EmailStr, ConfigDict, Field

from .models import RoleEnum, StatusEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: RoleEnum


class ProjectMemberAdd(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.viewer


class ProjectMemberRoleUpdate(BaseModel):
    role: RoleEnum

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    status: StatusEnum = StatusEnum.todo
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[StatusEnum] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: StatusEnum
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    created_at: datetime


class TaskAssign(BaseModel):
    user_id: Optional[uuid.UUID] = None


class PaginatedTasks(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TaskOut]
