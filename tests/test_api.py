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


def test_pagination(client, staff_headers):
    for i in range(5):
        client.post("/items", json={**ITEM, "name": f"Item {i}"}, headers=staff_headers)
    data = client.get("/items?page=2&limit=2", headers=staff_headers).json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


def test_roles(client, staff_headers, admin_headers):
    item_id = client.post("/items", json=ITEM, headers=staff_headers).json()["id"]
    assert client.delete(f"/items/{item_id}", headers=staff_headers).status_code == 403
    assert client.get("/users", headers=staff_headers).status_code == 403
    assert client.delete(f"/items/{item_id}", headers=admin_headers).status_code == 204