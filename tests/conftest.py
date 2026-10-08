import os

# Set BEFORE the app is imported, so tests never touch your real PostgreSQL database.
os.environ["SECRET_KEY"] = "test-secret-key-only-for-tests-123456"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User


def login(client, email, password):
    """Logs in and returns the Authorization header."""
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client():
    """A fresh, empty test database for every test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture()
def staff_headers(client):
    body = {"name": "Staff One", "email": "staff@example.com", "password": "password123"}
    client.post("/auth/signup", json=body)
    return login(client, body["email"], body["password"])


@pytest.fixture()
def admin_headers(client):
    # The admin is created directly in the database (in the real app: from .env).
    with SessionLocal() as db:
        db.add(User(name="Admin", email="admin@example.com", password_hash=hash_password("adminpass123"), role="admin"))
        db.commit()
    return login(client, "admin@example.com", "adminpass123")