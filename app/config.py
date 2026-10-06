"""All settings are read from environment variables (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5435/inventory_db"
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env and set it.")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60

# This account is created (or reset) as 'admin' on every startup.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Optional: needed only for Google login.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Websites (frontends) that are allowed to call this API from a browser (CORS).
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
