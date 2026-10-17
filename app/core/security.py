from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session
from app.config import ACCESS_TOKEN_MINUTES, GOOGLE_CLIENT_ID, JWT_ALGORITHM, SECRET_KEY
from app.database.database import get_db
from app.models.models import User

bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()



def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())



def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {"sub": str(user.id), "role": user.role, "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)



def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),) -> User:
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    try:
        claims = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user = db.get(User, int(claims["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user



def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Your role is not allowed to do this")
    return user



def require_admin_or_manager(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "inventory_manager"):
        raise HTTPException(403, "Your role is not allowed to do this")
    return user



def verify_google_token(token: str) -> dict:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google login is not configured")
    try:
        info = google_id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception:
        raise HTTPException(401, "Invalid Google token")
    if not info.get("email_verified"):
        raise HTTPException(401, "Google email is not verified")
    return info