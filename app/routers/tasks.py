import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import (
    get_current_user,
    get_project_or_404,
    get_membership,
    require_member,
    require_editor_or_owner,
)

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


def _get_task_or_404(project_id: uuid.UUID, task_id: uuid.UUID, db: Session) -> models.Task:
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.project_id == project_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _ensure_assignee_is_member(project_id: uuid.UUID, assignee_id: uuid.UUID, db: Session) -> None:
    if not get_membership(project_id, assignee_id, db):
        raise HTTPException(status_code=400, detail="Assignee must be a project member")


@router.post("", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: uuid.UUID,
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_editor_or_owner(project_id, current_user, db)

    if payload.assignee_id is not None:
        _ensure_assignee_is_member(project_id, payload.assignee_id, db)

    task = models.Task(project_id=project_id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=schemas.PaginatedTasks)
def list_tasks(
    project_id: uuid.UUID,
    status_filter: Optional[models.StatusEnum] = Query(default=None, alias="status"),
    assignee_id: Optional[uuid.UUID] = Query(default=None),
    due_before: Optional[date] = Query(default=None, description="Only tasks due on or before this date"),
    due_after: Optional[date] = Query(default=None, description="Only tasks due on or after this date"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_member(project_id, current_user, db)

    q = db.query(models.Task).filter(models.Task.project_id == project_id)
    if status_filter is not None:
        q = q.filter(models.Task.status == status_filter)
    if assignee_id is not None:
        q = q.filter(models.Task.assignee_id == assignee_id)
    if due_before is not None:
        q = q.filter(models.Task.due_date <= due_before)
    if due_after is not None:
        q = q.filter(models.Task.due_date >= due_after)

    total = q.count()
    items = (
        q.order_by(models.Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.PaginatedTasks(total=total, page=page, page_size=page_size, items=items)


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_member(project_id, current_user, db)
    return _get_task_or_404(project_id, task_id, db)


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_editor_or_owner(project_id, current_user, db)
    task = _get_task_or_404(project_id, task_id, db)

    data = payload.model_dump(exclude_unset=True)
    if data.get("assignee_id") is not None:
        _ensure_assignee_is_member(project_id, data["assignee_id"], db)

    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_editor_or_owner(project_id, current_user, db)
    task = _get_task_or_404(project_id, task_id, db)
    db.delete(task)
    db.commit()
    return None


@router.post("/{task_id}/assign", response_model=schemas.TaskOut)
def assign_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: schemas.TaskAssign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Assign a task to a project member, or unassign it by passing user_id: null."""
    require_editor_or_owner(project_id, current_user, db)
    task = _get_task_or_404(project_id, task_id, db)

    if payload.user_id is not None:
        _ensure_assignee_is_member(project_id, payload.user_id, db)

    task.assignee_id = payload.user_id
    db.commit()
    db.refresh(task)
    return task
