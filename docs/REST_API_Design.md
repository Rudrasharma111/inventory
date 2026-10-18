# REST API Design

Project: **Inventory Service** (FastAPI + PostgreSQL + JWT)
Base URL: `http://localhost:8000` | Format: JSON | Swagger: `/docs` | ReDoc: `/redoc`

This file explains the REST API of the project in simple English: what a REST API is, how the URLs are built, every endpoint, every request/response, and how one request travels through the code.

---

## 1. What is REST? (short)

REST is a style of building APIs over normal HTTP. Three ideas:

1. **Resources** - everything is a "thing" (noun) with its own URL: `items`, `users`.
2. **Methods** - the HTTP method says the action: `GET` read, `POST` create, `PUT` replace, `PATCH` small change, `DELETE` remove.
3. **Stateless** - the server does not remember you between requests. You send your JWT token every time.

Many URLs, one job per URL. The **HTTP status code** tells the result (200, 201, 404 ...).

---

## 2. Architecture flow (block diagram)

### 2.1 Big picture

```
 +-----------------+          HTTP + JSON           +---------------------------+
 |  Client         | -----------------------------> |  FastAPI app (port 8000)  |
 |  Postman /      |   Authorization: Bearer <JWT>  |                           |
 |  Swagger /      | <----------------------------- |  main.py                  |
 |  Frontend       |      status code + JSON        +-------------+-------------+
 +-----------------+                                              |
                                                                  v
                                                    +---------------------------+
                                                    |  PostgreSQL 15 (port 5435)|
                                                    |  tables: users, items     |
                                                    +---------------------------+
```

### 2.2 One request inside the code (example: `POST /items`)

```
 Client
   |  POST /items  + JWT + {"name":"Keyboard","quantity":10,"price":49.99}
   v
+----------------------------------------------------------------------+
| 1. CORS + Middleware (main.py)                                       |
|    start timer, later adds header X-Process-Time                     |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 2. Router (routers/items.py)  ->  finds  POST /items                 |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 3. Dependencies (auth.py)                                            |
|    get_current_user: check JWT signature + expiry, load user from DB |
|    (401 if token missing/bad)                                        |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 4. Pydantic schema ItemIn (schemas.py)                               |
|    name 1-100 chars, quantity >= 0, price 0.01..99999999.99          |
|    (422 if invalid)                                                  |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 5. Route function create_item()                                      |
|    Item(**data, created_by=user.id)  -> db.add -> db.commit          |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 6. SQLAlchemy model Item (models.py) -> PostgreSQL INSERT            |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 7. Response model ItemOut -> JSON, status 201                        |
+----------------------------------------------------------------------+
```

---

## 3. Resource structure

Plural nouns, lowercase, no verbs in the URL.

| Resource | URL | Meaning |
| :--- | :--- | :--- |
| auth | `/auth/signup`, `/auth/login`, `/auth/google` | Create account, get token |
| items | `/items`, `/items/{item_id}` | Inventory items |
| users | `/users`, `/users/{user_id}/role` | User list and roles (admin only) |
| health | `/health` | Is the service alive |

Relationship: one **user** creates many **items** (`items.created_by -> users.id`).

---

## 4. Endpoint list (URL + method)

| # | Method | URL | Who can call | Success | Errors |
| :-: | :--- | :--- | :--- | :-: | :--- |
| 1 | GET | `/health` | public | 200 | - |
| 2 | POST | `/auth/signup` | public | 201 | 409, 422 |
| 3 | POST | `/auth/login` | public | 200 | 401, 422 |
| 4 | POST | `/auth/google` | public | 200 | 401, 409, 503 |
| 5 | POST | `/items` | any logged-in user | 201 | 401, 422 |
| 6 | GET | `/items?page=&limit=` | any logged-in user | 200 | 401, 422 |
| 7 | GET | `/items/{item_id}` | any logged-in user | 200 | 401, 404 |
| 8 | PUT | `/items/{item_id}` | any logged-in user | 200 | 401, 404, 422 |
| 9 | DELETE | `/items/{item_id}` | inventory_manager, admin | 204 | 401, 403, 404 |
| 10 | GET | `/users` | admin | 200 | 401, 403 |
| 11 | PATCH | `/users/{user_id}/role` | admin | 200 | 400, 401, 403, 404, 422 |

Token header: `Authorization: Bearer <access_token>`

---

## 5. Request / response contract

### 5.1 POST `/auth/signup` (public)

Request:
```json
{ "name": "Rahul Sharma", "email": "rahul@example.com",  "password": "password123" }
```

| Field | Rule |
| :--- | :--- |
| name | required, 1-100 chars, spaces at both ends removed |
| email | required, valid email |
| password | required, 8-64 chars (max 72 bytes) |

Response `201`:
```json
{ "id": 2, "name": "Rahul Sharma", "email": "rahul@example.com", "role": "staff" }
```
Everybody starts as `staff`. A background task writes a "welcome message" to the log.

### 5.2 POST `/auth/login` (public)

Request: `{ "email": "rahul@example.com", "password": "password123" }`

Response `200`:
```json
{ "access_token": "<jwt>", "token_type": "bearer", "role": "staff" }
```
Wrong email or wrong password -> same `401` message (`Wrong email or password`).

### 5.3 POST `/auth/google` (public)

Request: `{ "id_token": "<Google ID token>" }`
Response `200`: same as login. New Google users get role `staff`.
If the email already has a password account -> `409` (accounts are never merged).

### 5.4 POST `/items` (logged in)

Request:
```json
{ "name": "Keyboard", "quantity": 10, "price": 49.99 }
```
Response `201`:
```json
{ "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 2 }
```
`created_by` always comes from the token. It cannot be sent in the body.

### 5.5 GET `/items` (logged in) - with pagination

| Query | Default | Rule |
| :--- | :--- | :--- |
| `page` | 1 | integer >= 1 |
| `limit` | 10 | integer 1-100 |

Example: `GET /items?page=2&limit=5`

Response `200`:
```json
{
  "page": 2, "limit": 5, "total": 12,
  "items": [ { "id": 7, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 2 } ]
}
```
How it works: `OFFSET (page-1)*limit LIMIT limit`, ordered by `id`. `total` is the number of all matches, so the client can build page numbers.

### 5.6 GET `/items/{item_id}` (logged in)
Response `200`: one item object. Missing id -> `404 {"detail":"Item not found"}`.

### 5.7 PUT `/items/{item_id}` (logged in)
Request: same body as create (all 3 fields needed, because PUT replaces). Response `200`: the updated item.

### 5.8 DELETE `/items/{item_id}` (manager or admin)
Response `204` with an empty body. Staff gets `403`.

### 5.9 GET `/users` (admin)
Response `200`: list of users. The password hash is never returned.

### 5.10 PATCH `/users/{user_id}/role` (admin)
Request: `{ "role": "inventory_manager" }` (only `inventory_manager` or `staff`)
Response `200`: the updated user.
The admin's role cannot be changed -> `400`. Nobody can be made admin -> `422`.

---

## 6. Status codes

| Code | Meaning in this project |
| :--- | :--- |
| 200 | OK |
| 201 | Created |
| 204 | Deleted, no body |
| 400 | Not allowed change (admin's role) |
| 401 | No token / bad token / expired token / wrong login |
| 403 | Logged in, but role not allowed |
| 404 | Item or user not found |
| 409 | Email already registered, or has a password account (Google) |
| 422 | Invalid body or query (Pydantic) |
| 503 | Google login not configured |

Error shape: `{ "detail": "Item not found" }`. For 422, `detail` is a list of invalid fields.

---

## 7. Role-based access

| Action | staff | inventory_manager | admin |
| :--- | :-: | :-: | :-: |
| Create / read / update items | yes | yes | yes |
| Delete items | no | yes | yes |
| List users, change roles | no | no | yes |

---

## 8. Idempotency

| Method | Idempotent | Why |
| :--- | :-: | :--- |
| GET | yes | only reads |
| PUT | yes | same body gives same final state |
| DELETE | yes | 2nd call gives 404 but nothing changes |
| PATCH role | yes | sets a fixed role |
| POST | no | each call creates a new row |

---

## 9. Example: how to build ONE endpoint in REST (`POST /items`)

**Step 1 - Schema** (`app/schemas.py`): what the client may send and what we return.
```python
class ItemIn(BaseModel):
    name: Name
    quantity: int = Field(ge=0)
    price: float = Field(ge=0.01, le=99999999.99)

class ItemOut(ItemIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: int
```

**Step 2 - Model** (`app/models.py`): the table.
```python
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
```

**Step 3 - Route** (`app/routers/items.py`):
```python
@router.post("", response_model=ItemOut, status_code=201)
def create_item(data: ItemIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    item = Item(**data.model_dump(), created_by=user.id)
    db.add(item); db.commit(); db.refresh(item)
    return item
```

**Step 4 - Register the router** (`app/main.py`): `app.include_router(items.router)`

**Step 5 - Call it**
```bash
curl -X POST http://localhost:8000/items \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"name":"Keyboard","quantity":10,"price":49.99}'
```

---

## 10. Why REST fits this project
- Simple CRUD on two tables.
- Works in browser, Postman, curl, Swagger with no extra tools.
- Easy to cache (`GET`) and easy to read status codes.
- FastAPI makes Swagger docs automatically from the schemas.