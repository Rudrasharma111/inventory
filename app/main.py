import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.core.security import get_user_by_email, hash_password
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD, CORS_ORIGINS, GOOGLE_CLIENT_ID
from app.database import SessionLocal
from app.pages.login_page import LOGIN_PAGE
from app.models import User
from app.routers import auth, items, users

def create_admin():
    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        return

    with SessionLocal() as db:
        user = get_user_by_email(db, ADMIN_EMAIL)
        if not user:
            user = User(name="Admin", email=ADMIN_EMAIL.lower())
            db.add(user)
        
        user.password_hash = hash_password(ADMIN_PASSWORD)
        user.role = "admin"
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_admin()
    yield

app = FastAPI(
    title="Inventory Service",
    version="1.0.0",
    description="Simple inventory REST API: FastAPI + PostgreSQL + JWT / Google login.",
    lifespan=lifespan,
)

# CORS lets a frontend running on another address (e.g. localhost:3000) call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Middleware: runs for every request and adds how long it took (see Postman > Headers)."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.1f}ms"
    return response

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(users.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page():
    """A small page with the 'Sign in with Google' button."""
    if not GOOGLE_CLIENT_ID:
        return HTMLResponse("Google login is not configured. Set GOOGLE_CLIENT_ID in .env", status_code=503)
    return LOGIN_PAGE.replace("YOUR_GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)