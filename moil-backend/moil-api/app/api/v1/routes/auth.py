from datetime import datetime, timedelta
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core import security as sec
from app.core.config import settings
from app.core.dependencies import current_user, audit
from app.db.session import get_db
from app.models import User, RefreshToken, ROLES
from app.schemas import RegisterIn, LoginIn, RefreshIn, TokenOut, UserOut
router = APIRouter(prefix="/auth", tags=["auth"])
def issue(db: Session, user: User) -> TokenOut:
    jti = sec.uuid.uuid4().hex
    db.add(RefreshToken(jti=sec.digest(jti), user_id=user.id, expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS))); db.commit()
    return TokenOut(access_token=sec.access_token(user.id), refresh_token=sec.refresh_token(user.id, jti))
@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if body.role not in ROLES: raise HTTPException(422, "Unknown role")
    if body.role == "ADMIN": raise HTTPException(403, "Admins are created by an existing admin")
    if db.scalar(select(User).where(User.email == body.email)): raise HTTPException(409, "Email already registered")
    u = User(email=body.email, name=body.name, password_hash=sec.hash_password(body.password), role=body.role)
    db.add(u); db.commit(); audit(db, u.id, "user.register"); return u
@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email))
    if u and u.locked_until and u.locked_until > datetime.utcnow(): raise HTTPException(423, "Account locked. Try again later.")
    if not u or not sec.verify_password(body.password, u.password_hash):
        if u:
            u.failed_attempts += 1
            if u.failed_attempts >= settings.MAX_FAILED_LOGINS: u.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES); u.failed_attempts = 0
            db.commit(); audit(db, u.id, "auth.login_failed")
        raise HTTPException(401, "Incorrect email or password")
    if not u.is_active: raise HTTPException(403, "This account is disabled. Contact an administrator.")
    u.failed_attempts = 0; db.commit(); audit(db, u.id, "auth.login"); return issue(db, u)
@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    try: data = sec.decode(body.refresh_token, "refresh")
    except jwt.PyJWTError: raise HTTPException(401, "Invalid refresh token")
    row = db.get(RefreshToken, sec.digest(data["jti"]))
    if not row or row.revoked:  # reuse of a rotated token: revoke the user's whole session family
        for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == int(data["sub"]))): t.revoked = True
        db.commit(); raise HTTPException(401, "Refresh token already used")
    row.revoked = True; db.commit()
    return issue(db, db.get(User, int(data["sub"])))
@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    try: row = db.get(RefreshToken, sec.digest(sec.decode(body.refresh_token, "refresh")["jti"]))
    except jwt.PyJWTError: return
    if row: row.revoked = True; db.commit()
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)): return user
class ChangePasswordIn(BaseModel): current_password: str; new_password: str = Field(min_length=8, max_length=128)
@router.post("/change-password", response_model=TokenOut)
def change_password(b: ChangePasswordIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not sec.verify_password(b.current_password, user.password_hash): raise HTTPException(400, "Current password is incorrect")
    if b.new_password == b.current_password: raise HTTPException(400, "New password must be different from the current one")
    user.password_hash = sec.hash_password(b.new_password); user.failed_attempts = 0
    for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)): t.revoked = True  # sign out other devices
    db.commit(); audit(db, user.id, "auth.password_change")
    return issue(db, user)  # fresh tokens keep this device signed in
