import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import create_access_token, get_user_by_email, hash_password, verify_google_token, verify_password
from app.database import get_db
from app.models import User
from app.schemas import GoogleLoginRequest, LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger("uvicorn.error")


def send_welcome_message(name: str, email: str) -> None:
    """Background task: runs after the response is sent (here it only writes a log line)."""
    logger.info("Welcome message sent to %s <%s>", name, email)

def save_new_user(db: Session, user: User) -> User:
    """Saves a new user. If the same email was saved a moment ago, the unique index stops us (409)."""
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    db.refresh(user)
    return user


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(data: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if get_user_by_email(db, data.email):
        raise HTTPException(409, "Email already registered")
    # everybody starts as "staff"; the role can never be chosen at signup
    user = User(name=data.name, email=data.email.lower(), phone=data.phone,
                password_hash=hash_password(data.password), role="staff")
    save_new_user(db, user)
    background_tasks.add_task(send_welcome_message, user.name, user.email)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, data.email)
    # same message for "no such user", "Google-only user" and "wrong password"
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    info = verify_google_token(data.id_token)
    user = get_user_by_email(db, info["email"])
    if user is None:
        email = info["email"].lower()
        user = save_new_user(db, User(name=info.get("name") or email.split("@")[0], email=email, role="staff"))
    elif user.password_hash:
        # never merge Google into a password account (emails are not verified at signup)
        raise HTTPException(409, "This email already has a password account. Log in with your password.")
    return TokenResponse(access_token=create_access_token(user), role=user.role)