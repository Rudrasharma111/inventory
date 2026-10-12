import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import create_access_token, hash_password, verify_google_token, verify_password
from app.database.database import get_db
from app.models.models import User
from app.schemas.schemas import GoogleLoginRequest, LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger("uvicorn.error")


def send_welcome_message(name: str, email: str) -> None:
    logger.info("Welcome message sent to %s <%s>", name, email)


def find_user(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def save_new_user(db: Session, user: User) -> None:
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already Registered")
    db.refresh(user)

@router.post("/signup", response_model=UserOut, status_code=201)
def signup(data: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if find_user(db, data.email):
        raise HTTPException(409, "Email already Registered")
    user = User(
        name=data.name,
        email=data.email.lower(),
        phone=data.phone,
        password_hash=hash_password(data.password),
        role="staff",
    )
    save_new_user(db, user)
    background_tasks.add_task(send_welcome_message, user.name, user.email)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = find_user(db, data.email)
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong email or Passsword")
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    info = verify_google_token(data.id_token)
    user = find_user(db, info["email"])
    if user is None:
        email = info["email"].lower()
        user = User(name=info.get("name") or email.split("@")[0], email=email, role="staff")
        save_new_user(db, user)
    elif user.password_hash:
        raise HTTPException(409, "This email already has a password account Log in with your password")
    return TokenResponse(access_token=create_access_token(user), role=user.role)