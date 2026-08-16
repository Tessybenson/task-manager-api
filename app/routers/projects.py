import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import (
    get_current_user,
    get_project_or_404,
    get_membership,
    require_member,
    require_owner,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = models.Project(name=payload.name, owner_id=current_user.id)
    db.add(project)
    db.flush()
    db.add(models.ProjectMember(project_id=project.id, user_id=current_user.id, role=models.RoleEnum.owner))
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[schemas.ProjectOut])
def list_my_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Project)
        .join(models.ProjectMember, models.ProjectMember.project_id == models.Project.id)
        .filter(models.ProjectMember.user_id == current_user.id)
        .all()
    )


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_member(project_id, current_user, db)
    return get_project_or_404(project_id, db)


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: uuid.UUID,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    membership = require_member(project_id, current_user, db)
    if membership.role not in (models.RoleEnum.owner, models.RoleEnum.editor):
        raise HTTPException(status_code=403, detail="Editor or owner role required")

    project = get_project_or_404(project_id, db)
    if payload.name is not None:
        project.name = payload.name
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_owner(project_id, current_user, db)
    project = get_project_or_404(project_id, db)
    db.delete(project)
    db.commit()
    return None

@router.post(
    "/{project_id}/members",
    response_model=schemas.ProjectMemberOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    project_id: uuid.UUID,
    payload: schemas.ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_owner(project_id, current_user, db)

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if get_membership(project_id, user.id, db):
        raise HTTPException(status_code=400, detail="User is already a member")

    membership = models.ProjectMember(project_id=project_id, user_id=user.id, role=payload.role)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@router.get("/{project_id}/members", response_model=list[schemas.ProjectMemberOut])
def list_members(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_member(project_id, current_user, db)
    return db.query(models.ProjectMember).filter(models.ProjectMember.project_id == project_id).all()


@router.patch("/{project_id}/members/{member_user_id}", response_model=schemas.ProjectMemberOut)
def update_member_role(
    project_id: uuid.UUID,
    member_user_id: uuid.UUID,
    payload: schemas.ProjectMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_owner(project_id, current_user, db)

    membership = get_membership(project_id, member_user_id, db)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{project_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: uuid.UUID,
    member_user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_owner(project_id, current_user, db)

    membership = get_membership(project_id, member_user_id, db)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    if membership.role == models.RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Cannot remove the project owner")

    db.delete(membership)
    db.commit()
    return None
