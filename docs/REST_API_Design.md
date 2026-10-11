# REST API Design

Base URL: `http://localhost:8000` · Format: JSON · Swagger docs: `/docs`

## 1. Resources and naming
Plural nouns, lowercase, no verbs in the URL. The HTTP method says what happens.

| Resource | URL |
| :--- | :--- |
| auth | `/auth/signup`, `/auth/login`, `/auth/google` |
| items | `/items`, `/items/{item_id}` |
| users (admin only) | `/users`, `/users/{user_id}/role` |
| health | `/health` |

| Action | Method + URL | Same pattern for a `users` resource |
| :--- | :--- | :--- |
| List | `GET /items` | `GET /users` |
| Read one | `GET /items/{id}` | `GET /users/{id}` |
| Create | `POST /items` | `POST /users` |
| Update | `PUT /items/{id}` | `PUT /users/{id}` |
| Delete | `DELETE /items/{id}` | `DELETE /users/{id}` |

## 2. Endpoints

| Method | URL | Who | Success | Errors |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/health` | public | 200 | - |
| POST | `/auth/signup` | public | 201 | 409 email exists, 422 invalid data |
| POST | `/auth/login` | public | 200 | 401 wrong email/password |
| POST | `/auth/google` | public | 200 | 401 invalid Google token, 409 email has a password account, 503 Google login not configured (used by the `/login` page) |
| POST | `/items` | logged in | 201 | 401, 422 |
| GET | `/items?page=1&limit=10&search=` | logged in | 200 | 401, 422 |
| GET | `/items/{item_id}` | logged in | 200 | 401, 404 |
| PUT | `/items/{item_id}` | logged in | 200 | 401, 404, 422 |
| DELETE | `/items/{item_id}` | **admin or inventory_manager** | 204 | 401, 403, 404 |
| GET | `/users` | **admin only** | 200 | 401, 403 |
| PATCH | `/users/{user_id}/role` | **admin only** | 200 | 400, 401, 403, 404, 422 |

Send the token as: `Authorization: Bearer <access_token>`

## 3. Request / response contracts

### POST `/auth/signup`
```json
{ "name": "Rahul Sharma", "email": "user@example.com", "phone": "+919876543210", "password": "password123" }
```
`name`: 1–100 characters, spaces at the ends are removed (required) · `email`: valid email (required) · `phone`: 7–15 digits, optional `+` at the start (optional) · `password`: 8–64 characters, at most 72 bytes (required). Response `201`:
```json
{ "id": 1, "name": "Rahul Sharma", "email": "user@example.com", "phone": "+919876543210", "role": "staff" }
```
Everybody who signs up gets the role `staff`.

### POST `/auth/login`
```json
{ "email": "user@example.com", "password": "password123" }
```
Response `200`:
```json
{ "access_token": "<jwt>", "token_type": "bearer", "role": "staff" }
```
There is no login rate limiting (see the README, Known limitations).

### POST `/auth/google`
```json
{ "id_token": "<Google ID token>" }
```
Response `200`: same as login (new Google users get role `staff`). An email that already has a password account gets `409` (accounts are never merged, because signup does not verify emails).

### POST `/items` and PUT `/items/{item_id}`
```json
{ "name": "Keyboard", "quantity": 10, "price": 49.99 }
```
`name`: 1–100 characters (required) · `quantity`: integer >= 0, where 0 means out of stock (required) · `price`: number from 0.01 to 99999999.99, stored with 2 decimals (required).
Response `201` (create) / `200` (update):
```json
{ "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 1 }
```

### GET `/items`
Query: `page` (default 1) · `limit` (default 10, max 100) · `search` (optional, part of the name, not case sensitive). Response `200`:
```json
{
  "page": 1, "limit": 10, "total": 25,
  "items": [ { "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 1 } ]
}
```

### DELETE `/items/{item_id}`
Response `204` (empty body).

### GET `/users` (admin only)
Response `200`:
```json
[ { "id": 1, "name": "Rahul Sharma", "email": "user@example.com", "phone": "+919876543210", "role": "staff" } ]
```

### PATCH `/users/{user_id}/role` (admin only)
```json
{ "role": "inventory_manager" }
```
`role` must be `"inventory_manager"` or `"staff"` (nobody can be made `admin`). Response `200`:
```json
{ "id": 1, "name": "Rahul Sharma", "email": "user@example.com", "phone": "+919876543210", "role": "inventory_manager" }
```
The admin's own role cannot be changed (`400`). The new role works immediately (the server reads the role from the database).

## 4. Status codes used
| Code | Meaning here |
| :--- | :--- |
| 200 / 201 / 204 | OK / created / deleted (no body) |
| 400 | Not allowed change (the admin's role) |
| 401 | No token, bad token, expired token, or wrong login |
| 403 | Logged in, but the role is not allowed |
| 404 | Item or user not found |
| 409 | Email already registered / email has a password account |
| 422 | Request body or query is invalid (Pydantic) |
| 503 | Google login is not configured on the server (no `GOOGLE_CLIENT_ID`) |

Errors look like `{ "detail": "Item not found" }`. For `422`, `detail` lists the invalid fields.
Every response has the header `X-Process-Time` (how long the request took, added by a middleware).

## 5. Idempotency
`GET`, `PUT`, `DELETE` are idempotent (repeating them leaves the same final state; a repeated `DELETE` gives `404` the second time, but nothing changes). `POST` is not idempotent: each call creates a new row. `PATCH` is idempotent here because it sets a fixed role.