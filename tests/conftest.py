import os
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
import pytest
from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.core.security import hash_password


def login(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture()
def staff_headers(client):
    client.post("/auth/signup", json={"name": "Staff", "email": "staff@example.com", "password": "password123"})
    return login(client, "staff@example.com", "password123")


@pytest.fixture()
def admin_headers(client):
    with SessionLocal() as db:
        db.add(User(name="Admin", email="admin@example.com", password_hash=hash_password("adminpass123"), role="admin"))
        db.commit()
    return login(client, "admin@example.com", "adminpass123")