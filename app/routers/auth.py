"""Endpoints: /auth/signup, /auth/login, /auth/google."""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    hash_password,
    verify_google_token,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas import GoogleLoginRequest, LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger("uvicorn.error")


def send_welcome_message(name: str, email: str) -> None:
    """Background task: runs after the response is sent (here it only writes a log line)."""
    logger.info("Welcome message sent to %s <%s>", name, email)


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(data: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    # everybody starts as "staff"; the role can never be chosen at signup
    user = User(
        name=data.name,
        email=email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role="staff",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # two signups with the same email at the same moment: the unique index stops the second
        db.rollback()
        raise HTTPException(409, "Email already registered")
    db.refresh(user)
    background_tasks.add_task(send_welcome_message, user.name, user.email)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    # same message for "no such user", "Google-only user" and "wrong password"
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    info = verify_google_token(data.id_token)
    email = info["email"].lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(name=info.get("name") or email.split("@")[0], email=email, role="staff")
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Email already registered")
        db.refresh(user)
    elif user.password_hash:
        # never merge Google into a password account (emails are not verified at signup)
        raise HTTPException(409, "This email already has a password account. Log in with your password.")
    return TokenResponse(access_token=create_access_token(user), role=user.role)