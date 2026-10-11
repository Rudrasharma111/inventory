import os
from dotenv import load_dotenv

load_dotenv()  

EXAMPLE_PREFIX = "change-me"  # sample values in .envexample Start With This text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5435/inventory_db")
SECRET_KEY = os.getenv("SECRET_KEY")

# Stop the app if the key is missing or is   Still the sample value
if not SECRET_KEY or SECRET_KEY.startswith(EXAMPLE_PREFIX):
    raise RuntimeError("SECRET_KEY is missing or still the example v Set a real one in .env.")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")  # this admin is Created    on every startup
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if ADMIN_PASSWORD and ADMIN_PASSWORD.startswith(EXAMPLE_PREFIX):
    raise RuntimeError("ADMIN_PASSWORD still the example value Set a real one in .env.")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")  # only needed For Google login

# Websites Allowed to call this API from a browser CORS
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]