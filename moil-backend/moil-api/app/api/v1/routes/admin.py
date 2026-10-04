from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core import security as sec
from app.core.dependencies import require_roles, audit
from app.db.session import get_db
from app.models import User, RefreshToken, AuditLog, ROLES
router = APIRouter(prefix="/admin", tags=["admin"])
ADMIN = require_roles()  # no extra roles listed, so admin only


class UserCreate(BaseModel):
    email: EmailStr; name: str = Field(min_length=2, max_length=120); password: str = Field(min_length=8, max_length=128); role: str
class UserPatch(BaseModel): role: str | None = None; is_active: bool | None = None; unlock: bool | None = None
class PasswordIn(BaseModel): password: str = Field(min_length=8, max_length=128)


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "is_active": u.is_active,
            "locked": bool(u.locked_until and u.locked_until > datetime.utcnow())}


def _revoke_sessions(db: Session, user_id: int):
    for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id)): t.revoked = True


def _get(db: Session, id: int) -> User:
    u = db.get(User, id)
    if not u: raise HTTPException(404, "User not found")
    return u


@router.get("/users")
def users(db: Session = Depends(get_db), _=Depends(ADMIN)):
    return [user_out(u) for u in db.scalars(select(User).order_by(User.name, User.id))]


@router.post("/users", status_code=201)
def create_user(b: UserCreate, db: Session = Depends(get_db), me: User = Depends(ADMIN)):
    if b.role not in ROLES: raise HTTPException(422, "Unknown role")
    if db.scalar(select(User).where(User.email == b.email)): raise HTTPException(409, "That email is already registered")
    u = User(email=b.email, name=b.name.strip(), password_hash=sec.hash_password(b.password), role=b.role)
    db.add(u); db.commit()
    audit(db, me.id, "admin.user_create", target_user_id=u.id, email=u.email, role=u.role)
    return user_out(u)


@router.patch("/users/{id}")
def update_user(id: int, b: UserPatch, db: Session = Depends(get_db), me: User = Depends(ADMIN)):
    u = _get(db, id); changes = {}
    if id == me.id and ((b.role is not None and b.role != u.role) or b.is_active is False):
        raise HTTPException(409, "You cannot change your own role or disable your own account")
    if b.role is not None and b.role != u.role:
        if b.role not in ROLES: raise HTTPException(422, "Unknown role")
        changes["role"] = [u.role, b.role]; u.role = b.role
    if b.is_active is not None and b.is_active != u.is_active:
        changes["is_active"] = [u.is_active, b.is_active]; u.is_active = b.is_active
        if not b.is_active: _revoke_sessions(db, u.id)  # signs the user out everywhere
    if b.unlock: u.locked_until = None; u.failed_attempts = 0; changes["unlocked"] = True
    if not changes: return user_out(u)
    db.commit(); audit(db, me.id, "admin.user_update", target_user_id=u.id, email=u.email, **changes)
    return user_out(u)


@router.post("/users/{id}/reset-password", status_code=204)
def reset_password(id: int, b: PasswordIn, db: Session = Depends(get_db), me: User = Depends(ADMIN)):
    u = _get(db, id)
    u.password_hash = sec.hash_password(b.password); u.failed_attempts = 0; u.locked_until = None
    _revoke_sessions(db, u.id); db.commit()
    audit(db, me.id, "admin.password_reset", target_user_id=u.id, email=u.email)  # the password itself is never logged


@router.get("/audit-logs")
def audit_logs(page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), action: str | None = None,
               days: int | None = Query(None, ge=1, le=3650), db: Session = Depends(get_db), _=Depends(ADMIN)):
    q = select(AuditLog, User.email, User.name).outerjoin(User, User.id == AuditLog.user_id)
    if action: q = q.where(AuditLog.action == action)
    if days: q = q.where(AuditLog.at >= datetime.utcnow() - timedelta(days=days))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(AuditLog.id.desc()).limit(size).offset((page - 1) * size)).all()
    return {"items": [{"id": a.id, "at": a.at, "action": a.action, "detail": a.detail, "user_email": email, "user_name": name}
                      for a, email, name in rows], "total": total, "page": page, "size": size}


@router.get("/audit-actions")
def audit_actions(db: Session = Depends(get_db), _=Depends(ADMIN)):
    return list(db.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action)))
