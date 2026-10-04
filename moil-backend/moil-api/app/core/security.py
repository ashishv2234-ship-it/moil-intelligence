import uuid, hashlib
from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from app.core.config import settings
def hash_password(p: str) -> str: return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p: str, h: str) -> bool: return bcrypt.checkpw(p.encode(), h.encode())
def _token(sub: str, kind: str, delta: timedelta, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": sub, "type": kind, "jti": jti or uuid.uuid4().hex, "iat": now, "exp": now + delta}, settings.SECRET_KEY, "HS256")
def access_token(user_id: int) -> str: return _token(str(user_id), "access", timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))
def refresh_token(user_id: int, jti: str) -> str: return _token(str(user_id), "refresh", timedelta(days=settings.REFRESH_TOKEN_DAYS), jti)
def decode(token: str, kind: str) -> dict:
    data = jwt.decode(token, settings.SECRET_KEY, ["HS256"])
    if data.get("type") != kind: raise jwt.InvalidTokenError("wrong token type")
    return data
def digest(s: str) -> str: return hashlib.sha256(s.encode()).hexdigest()
