import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .auth import decode_access_token
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_exception
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_project_or_404(project_id: uuid.UUID, db: Session) -> models.Project:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_membership(project_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> Optional[models.ProjectMember]:
    return (
        db.query(models.ProjectMember)
        .filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == user_id,
        )
        .first()
    )


def require_member(project_id: uuid.UUID, user: models.User, db: Session) -> models.ProjectMember:
    """Any role (owner/editor/viewer) may pass. Raises 404 if the project
    doesn't exist at all, 403 if it exists but the user isn't on it."""
    get_project_or_404(project_id, db)
    membership = get_membership(project_id, user.id, db)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return membership


def require_editor_or_owner(project_id: uuid.UUID, user: models.User, db: Session) -> models.ProjectMember:
    membership = require_member(project_id, user, db)
    if membership.role not in (models.RoleEnum.owner, models.RoleEnum.editor):
        raise HTTPException(status_code=403, detail="Editor or owner role required")
    return membership


def require_owner(project_id: uuid.UUID, user: models.User, db: Session) -> models.ProjectMember:
    membership = require_member(project_id, user, db)
    if membership.role != models.RoleEnum.owner:
        raise HTTPException(status_code=403, detail="Owner role required")
    return membership
