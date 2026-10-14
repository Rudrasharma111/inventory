from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD, CORS_ORIGINS, GOOGLE_CLIENT_ID
from app.database import SessionLocal
from app.pages.login_page import LOGIN_PAGE
from app.models import User
from app.routers import auth, items, users
from app.core.security import hash_password

def create_admin():
    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        return
    with SessionLocal() as db:
        email = ADMIN_EMAIL.lower()
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(name="Admin", email=email)
            db.add(user)
        user.password_hash = hash_password(ADMIN_PASSWORD)
        user.role = "admin"
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_admin()
    yield

app = FastAPI(title="Inventory Service", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(users.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page():
    if not GOOGLE_CLIENT_ID:
        return HTMLResponse("Google login is not configured. Set GOOGLE_CLIENT_ID in .env", status_code=503)
    return LOGIN_PAGE.replace("YOUR_GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)