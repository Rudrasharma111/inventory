from tests.conftest import login

ITEM = {"name": "Keyboard", "quantity": 10, "price": 49.99}
SIGNUP = {"name": "Test User", "email": "user@example.com", "password": "password123"}


def test_signup_and_login(client):
    assert client.post("/auth/signup", json=SIGNUP).status_code == 201
    assert client.post("/auth/signup", json=SIGNUP).status_code == 409  # same email again
    ok = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert ok.status_code == 200 and "access_token" in ok.json()
    bad = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "wrong-pass"})
    assert bad.status_code == 401


def test_item_crud(client, staff_headers):
    assert client.get("/items").status_code == 401  # no token
    item_id = client.post("/items", json=ITEM, headers=staff_headers).json()["id"]
    assert client.get(f"/items/{item_id}", headers=staff_headers).status_code == 200
    r = client.put(f"/items/{item_id}", json={**ITEM, "quantity": 3}, headers=staff_headers)
    assert r.json()["quantity"] == 3
    assert client.post("/items", json={**ITEM, "quantity": -1}, headers=staff_headers).status_code == 422


def test_roles(client, staff_headers, admin_headers):
    item_id = client.post("/items", json=ITEM, headers=staff_headers).json()["id"]
    assert client.delete(f"/items/{item_id}", headers=staff_headers).status_code == 403  # staff
    assert client.delete(f"/items/{item_id}", headers=admin_headers).status_code == 204  # admin