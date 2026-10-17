import os
import pytest
from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.core.security import hash_password

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

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



ITEM = {"name": "Keyboard", "quantity": 10, "price": 49.99}
USER = {"name": "Test User", "email": "user@example.com", "password": "password123"}



def test_signup_and_login(client):
    assert client.post("/auth/signup", json=USER).status_code == 201
    assert client.post("/auth/signup", json=USER).status_code == 409

    ok = client.post("/auth/login", json={"email": USER["email"], "password": USER["password"]})
    assert "access_token" in ok.json()
    
    wrong = client.post("/auth/login", json={"email": USER["email"], "password": "wrong-pass"})
    assert wrong.status_code == 401


def test_item_crud(client, staff_headers):
    assert client.get("/items").status_code == 401
    
    item_id = client.post("/items", json=ITEM, headers=staff_headers).json()["id"]
    
    assert client.get(f"/items/{item_id}", headers=staff_headers).status_code == 200
    
    updated = client.put(f"/items/{item_id}", json={**ITEM, "quantity": 3}, headers=staff_headers)
    assert updated.json()["quantity"] == 3
    
    assert client.post("/items", json={**ITEM, "quantity": -1}, headers=staff_headers).status_code == 422


def test_roles(client, staff_headers, admin_headers):
    # Staff ek item banata hai
    item_id = client.post("/items", json=ITEM, headers=staff_headers).json()["id"]
    
    assert client.delete(f"/items/{item_id}", headers=staff_headers).status_code == 403
    
    assert client.get("/users", headers=staff_headers).status_code == 403
    
    assert client.delete(f"/items/{item_id}", headers=admin_headers).status_code == 204