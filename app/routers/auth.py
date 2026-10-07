import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_google_token, verify_password
from app.database import get_db
from app.models import User
from app.schemas import GoogleLoginRequest, LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])

def send_welcome_message(name: str, email: str):
    """Background task: runs after the signup response is sent (pretend email)."""
    logging.getLogger("uvicorn.error").info("Welcome message sent to %s (%s)", name, email)


def token_response(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user), role=user.role)


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(data: SignupRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(
        name=data.name,
        email=email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role="staff",  # everybody starts as staff
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    background.add_task(send_welcome_message, user.name, user.email)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.lower()
    user = db.query(User).filter(User.email == email).first()
    # Google-only users have no password, so they can never log in here.
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    return token_response(user)


@router.post("/google", response_model=TokenResponse, include_in_schema=False)  # used by /login page
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    info = verify_google_token(data.id_token)
    email = info["email"].lower()
    user = db.query(User).filter(User.email == email).first()
    if user and user.password_hash:
        # Anyone can sign up with any email (we do not verify emails), so we never
        # merge a Google login into a password account. Otherwise a stranger who
        # signed up with your email first could stay inside your account.
        raise HTTPException(409, "This email has a password account. Log in with email and password.")
    if not user:
        user = User(name=info.get("name") or email.split("@")[0], email=email, role="staff")
        db.add(user)
        db.commit()
        db.refresh(user)
    return token_response(user)