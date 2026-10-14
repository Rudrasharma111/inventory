from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import GoogleLoginRequest, LoginRequest, SignupRequest, TokenResponse, UserOut
from app.core.security import create_access_token, hash_password, verify_google_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


def find_user(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()

def create_user(db: Session, name: str, email: str, password_hash: str | None = None) -> User:
    user = User(name=name, email=email.lower(), password_hash=password_hash, role="staff")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/signup", response_model=UserOut, status_code=201)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    if find_user(db, data.email):
        raise HTTPException(409, "Email already registered")
    return create_user(db, data.name, data.email, hash_password(data.password))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = find_user(db, data.email)
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    info = verify_google_token(data.id_token)
    user = find_user(db, info["email"])
    if user is None:
        name = info.get("name") or info["email"].split("@")[0]
        user = create_user(db, name, info["email"])
    elif user.password_hash:
        raise HTTPException(409, "This email has a password account. Log in with your password")
    return TokenResponse(access_token=create_access_token(user), role=user.role)