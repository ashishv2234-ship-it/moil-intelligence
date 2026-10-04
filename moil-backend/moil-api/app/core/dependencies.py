from datetime import datetime
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode
from app.db.session import get_db
from app.models import User, AuditLog
bearer = HTTPBearer(auto_error=False)
def current_user(cred=Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not cred: raise HTTPException(401, "Not authenticated")
    try: data = decode(cred.credentials, "access")
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, int(data["sub"]))
    if not user or not user.is_active: raise HTTPException(401, "User inactive")
    return user
def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role != "ADMIN" and user.role not in roles: raise HTTPException(403, "Your role cannot do this")
        return user
    return dep
def audit(db: Session, user_id: int | None, action: str, **detail):
    db.add(AuditLog(user_id=user_id, action=action, detail=detail, at=datetime.utcnow())); db.commit()
