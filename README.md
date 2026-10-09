# Inventory Service

A backend service to manage inventory items. Users sign up or log in (email + password, or Google), get a **JWT token**, and use it to create, read, update and delete items. What a user may do depends on their **role**. Everything runs with one Docker command.

**Stack:** Python 3.11 · FastAPI · PostgreSQL 15 · SQLAlchemy · Alembic · Pydantic · JWT · Docker Compose · pytest

---

## Table of contents

1. [Project at a glance](#1-project-at-a-glance)
2. [M4 requirement checklist](#2-m4-requirement-checklist)
3. [Project structure](#3-project-structure)
4. [Architecture and project flow](#4-architecture-and-project-flow)
5. [Database design](#5-database-design)
6. [API documentation](#6-api-documentation)
7. [Authentication, JWT and roles](#7-authentication-jwt-and-roles)
8. [Validation rules](#8-validation-rules)
9. [Setup and run](#9-setup-and-run)
10. [Database migrations (Alembic)](#10-database-migrations-alembic)
11. [Tests](#11-tests)
12. [Postman collection](#12-postman-collection)
13. [Design documents](#13-design-documents)
14. [Known limitations](#14-known-limitations)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Project at a glance

| Fact | Value |
| :--- | :--- |
| Purpose | Manage inventory items with login, roles and a database |
| Language / framework | Python 3.11 · FastAPI |
| Database | PostgreSQL 15 (2 tables: `users`, `items`) |
| Auth | JWT (HS256, 60 minutes) + Google Sign-In |
| Roles | 3: `staff`, `inventory_manager`, `admin` |
| REST endpoints | 10, plus `POST /auth/google` and the `/login` page for Google |
| Docker services | 3: `db` (PostgreSQL), `pgadmin`, `web` (the API) |
| Automated tests | 3 tests (pytest) |
| Application code | about 430 lines in 11 small files |

| URL | What you get |
| :--- | :--- |
| http://localhost:8000/docs | Swagger UI: try every endpoint in the browser |
| http://localhost:8000/redoc | ReDoc documentation |
| http://localhost:8000/health | Health check |
| http://localhost:8000/login | "Sign in with Google" page |
| http://localhost:5050 | pgAdmin: look at the database tables |

---

## 2. M4 requirement checklist

### Must submit

| Requirement | Status | Where |
| :--- | :---: | :--- |
| Git repository | ✅ | this repo |
| `REST_API_Design.md` | ✅ | [docs/REST_API_Design.md](docs/REST_API_Design.md) |
| FastAPI service | ✅ | `app/` |
| Auth | ✅ | `app/auth.py`, `app/routers/auth.py` |
| PostgreSQL integration | ✅ | `app/database.py`, `app/models.py` (SQLAlchemy) |
| `GraphQL_Design.md` | ✅ | [docs/GraphQL_Design.md](docs/GraphQL_Design.md) |
| `gRPC_Design.md` | ✅ | [docs/gRPC_Design.md](docs/gRPC_Design.md) |
| `Database_Design.md` (ERD, tables, relationships, PK/FK) | ✅ | [docs/Database_Design.md](docs/Database_Design.md), [docs/erd.svg](docs/erd.svg) |
| `JWT_Design.md` | ✅ | [docs/JWT_Design.md](docs/JWT_Design.md) |
| Dockerfile | ✅ | `Dockerfile` (and `docker-compose.yml`) |
| README: API endpoints | ✅ | [Section 6](#6-api-documentation) |
| README: setup instructions | ✅ | [Section 9](#9-setup-and-run) |
| README: architecture explanation | ✅ | [Section 4](#4-architecture-and-project-flow) |
| README: Postman collection | ✅ | [Section 12](#12-postman-collection) |
| README: 3–5 unit tests | ✅ | [Section 11](#11-tests) (3 tests) |

### Stretch goals

| Goal | Status | Where |
| :--- | :---: | :--- |
| Pagination on a REST API | ✅ | `GET /items?page=1&limit=10` (also `search`) |
| Social login with Google | ✅ | `POST /auth/google` and the `/login` page |
| Role-based access | ✅ | 3 roles, checked by `require_roles(...)` |
| Swagger / OpenAPI docs | ✅ | `/docs` and `/redoc` (generated automatically) |

### Course topics used in this project

| Topic from the course | Where it is used |
| :--- | :--- |
| REST methods, status codes, idempotency | [Section 6](#6-api-documentation) |
| Pydantic models and validators | `app/schemas.py` |
| SQLAlchemy ORM, queries, connection pooling | `app/models.py`, `app/database.py`, `app/routers/` |
| Database migrations | `alembic/` ([Section 10](#10-database-migrations-alembic)) |
| JWT and OAuth login | `app/auth.py` |
| Middleware | `add_process_time_header` in `app/main.py` |
| Background task | `send_welcome_message` in `app/routers/auth.py` |
| CORS | `CORSMiddleware` in `app/main.py` |
| dotenv | `app/config.py` |
| pytest fixtures | `tests/` |
| Docker + Docker Compose (PostgreSQL + pgAdmin) | `Dockerfile`, `docker-compose.yml` |

---

## 3. Project structure

```
inventory-service/
├── app/
│   ├── main.py             # creates the app, CORS, middleware, creates the admin on startup
│   ├── config.py           # reads settings from .env
│   ├── database.py         # database engine and session (one session per request)
│   ├── models.py           # the 2 tables: User, Item
│   ├── schemas.py          # Pydantic models: validate requests, shape responses
│   ├── auth.py             # password hashing, JWT, "who is logged in", role checks, Google check
│   ├── login_page.py       # small HTML page with the "Sign in with Google" button
│   └── routers/
│       ├── auth.py         # /auth/signup, /auth/login, /auth/google
│       ├── items.py        # /items (CRUD, pagination, search)
│       └── users.py        # /users (admin only)
├── alembic/                # database migrations
│   └── versions/0001_create_users_and_items.py
├── tests/
│   ├── conftest.py         # fixtures: test client, staff login, admin login
│   └── test_api.py         # the 3 tests
├── docs/
│   ├── REST_API_Design.md
│   ├── GraphQL_Design.md
│   ├── gRPC_Design.md
│   ├── Database_Design.md  # and erd.svg
│   ├── JWT_Design.md
│   └── postman_collection.json
├── Dockerfile
├── docker-compose.yml      # db + pgadmin + web
├── alembic.ini
├── pytest.ini
├── requirements.txt        # all packages (app + pytest and httpx for tests)
├── .env.example            # template for your .env
└── README.md
```

---

## 4. Architecture and project flow

### 4.1 Layers (who does what)

| Layer | File | Job |
| :--- | :--- | :--- |
| Routers | `app/routers/*.py` | Receive the request, call the logic, return the response |
| Schemas | `app/schemas.py` | Pydantic checks the incoming data and shapes the outgoing data |
| Auth | `app/auth.py` | Hash passwords, create and check JWTs, check roles |
| Models | `app/models.py` | Python classes that map to the tables |
| Database | `app/database.py` | Connection pool and one session per request |

### 4.2 Life of a protected request

Example: `DELETE /items/5` with a token.

1. The middleware starts a timer and passes the request on.
2. `get_current_user` checks the token signature and expiry, then loads the user from the database (so the role is the **current** one).
3. `require_roles` checks that the role is `admin` or `inventory_manager`.
4. The item is found and deleted, and the response is `204 No Content` with the header `X-Process-Time`.

Status codes along this path: no or bad token → **401**, role not allowed → **403**, invalid body or query → **422**, missing item → **404**.

### 4.3 Email + password login

1. `POST /auth/signup` → the password is hashed with bcrypt and saved. The new user gets the role `staff`. A background task writes a "welcome message" to the log after the response is sent.
2. `POST /auth/login` → the server finds the user by email and checks the password hash. If both are correct, it returns a JWT.
3. The client sends that JWT in the `Authorization: Bearer <token>` header with every request.

### 4.4 Google Sign-In

1. The user opens `/login` and clicks "Sign in with Google".
2. Google gives the browser a Google ID token.
3. The browser sends `POST /auth/google` with `{id_token}`.
4. The API verifies the token (signature, expiry, our client id), then finds or creates the user (role `staff`).
5. The API returns our own JWT.

Rule: if the email already has a **password account**, Google login is rejected with `409`. Emails are not verified at signup, so merging could let a stranger who registered your email first stay inside your account.

---

## 5. Database design

PostgreSQL 15 with two tables. Tables are created by Alembic migrations (see [Section 10](#10-database-migrations-alembic)).

The ERD diagram is in [docs/erd.svg](docs/erd.svg) and in the presentation.

### `users`

| Column | Type | Constraints |
| :--- | :--- | :--- |
| id | INTEGER | PRIMARY KEY (auto number) |
| name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| phone | VARCHAR(20) | NULL allowed |
| password_hash | VARCHAR(255) | NULL allowed (Google users have no password) |
| role | VARCHAR(20) | NOT NULL (`admin`, `inventory_manager`, `staff`) |

### `items`

| Column | Type | Constraints |
| :--- | :--- | :--- |
| id | INTEGER | PRIMARY KEY (auto number) |
| name | VARCHAR(100) | NOT NULL, indexed (used by search) |
| quantity | INTEGER | NOT NULL (the API requires >= 0; 0 = out of stock) |
| price | NUMERIC(10,2) | NOT NULL (exact decimal, so money has no rounding errors) |
| created_by | INTEGER | NOT NULL, FOREIGN KEY → `users.id` |

### Relationships and keys

- One `user` creates many `items` (`items.created_by → users.id`, one-to-many).
- Primary keys: `users.id`, `items.id`. Foreign key: `items.created_by`. Unique key: `users.email`.
- A user who has created items cannot be deleted from the database (the foreign key protects the items).

---

## 6. API documentation

Base URL: `http://localhost:8000` · Format: JSON · Interactive docs: `/docs`
Send the token as `Authorization: Bearer <access_token>`. In Swagger click **Authorize** and paste **only the token** (without the word `Bearer`).

### 6.1 Endpoints

| # | Method | URL | Who | Success | Errors |
| :-: | :--- | :--- | :--- | :-: | :--- |
| 1 | GET | `/health` | public | 200 | - |
| 2 | POST | `/auth/signup` | public | 201 | 409, 422 |
| 3 | POST | `/auth/login` | public | 200 | 401, 422 |
| 4 | POST | `/auth/google` | public (used by the `/login` page) | 200 | 401, 409, 503 |
| 5 | POST | `/items` | any logged-in user | 201 | 401, 422 |
| 6 | GET | `/items?page=&limit=&search=` | any logged-in user | 200 | 401, 422 |
| 7 | GET | `/items/{item_id}` | any logged-in user | 200 | 401, 404 |
| 8 | PUT | `/items/{item_id}` | staff (own items only), manager, admin | 200 | 401, 403, 404, 422 |
| 9 | DELETE | `/items/{item_id}` | manager, admin | 204 | 401, 403, 404 |
| 10 | GET | `/users` | admin | 200 | 401, 403 |
| 11 | PATCH | `/users/{user_id}/role` | admin | 200 | 400, 401, 403, 404, 422 |

### 6.2 Examples

**POST `/auth/signup`**
```json
{ "name": "Rahul Sharma", "email": "rahul@example.com", "phone": "+919876543210", "password": "password123" }
```
`201`:
```json
{ "id": 2, "name": "Rahul Sharma", "email": "rahul@example.com", "phone": "+919876543210", "role": "staff" }
```

**POST `/auth/login`**
```json
{ "email": "rahul@example.com", "password": "password123" }
```
`200`:
```json
{ "access_token": "<jwt>", "token_type": "bearer", "role": "staff" }
```

**POST `/items`** and **PUT `/items/{item_id}`**
```json
{ "name": "Keyboard", "quantity": 10, "price": 49.99 }
```
`201` (create) / `200` (update):
```json
{ "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 2 }
```

**GET `/items?page=1&limit=5&search=key`**

| Query | Default | Rule |
| :--- | :--- | :--- |
| `page` | 1 | integer >= 1 |
| `limit` | 10 | integer from 1 to 100 |
| `search` | none | part of the item name, not case sensitive |

`200`:
```json
{
  "page": 1, "limit": 5, "total": 1,
  "items": [ { "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 2 } ]
}
```

**DELETE `/items/{item_id}`** → `204` with an empty body.

**GET `/users`** (admin) → list of users (never includes the password hash).

**PATCH `/users/{user_id}/role`** (admin)
```json
{ "role": "inventory_manager" }
```
`role` must be `inventory_manager` or `staff`. Nobody can be made `admin`, and the admin's own role cannot be changed (`400`).

### 6.3 Status codes used

| Code | Meaning here |
| :--- | :--- |
| 200 / 201 / 204 | OK / created / deleted (no body) |
| 400 | Change not allowed (the admin's role) |
| 401 | No token, bad or expired token, or wrong login |
| 403 | Logged in, but the role is not allowed |
| 404 | Item or user not found |
| 409 | Email already registered, or email has a password account (Google) |
| 422 | Request body or query is invalid (Pydantic) |
| 503 | Google login is not configured |

Errors look like `{ "detail": "Item not found" }`. For `422`, `detail` lists the invalid fields.
Every response has an `X-Process-Time` header (added by the middleware).

### 6.4 Idempotency

| Method | Idempotent? | Why |
| :--- | :---: | :--- |
| GET | ✅ | Only reads |
| PUT | ✅ | Same body gives the same final state |
| DELETE | ✅ | The second call returns `404`, but nothing changes |
| PATCH (role) | ✅ | Sets a fixed role |
| POST | ❌ | Each call creates a new row |

---

## 7. Authentication, JWT and roles

### 7.1 JWT

- Library: PyJWT · Algorithm: **HS256** · Secret: `SECRET_KEY` · Lifetime: **60 minutes**.
- Claims: `sub` (user id), `email`, `role`, `iat`, `exp`. Full details: [docs/JWT_Design.md](docs/JWT_Design.md).
- The **role is read from the database on every request, not from the token**. So a role change (or a deleted user) works immediately and the user does not need to log in again.

### 7.2 Roles and permissions

| Action | staff | inventory_manager | admin |
| :--- | :---: | :---: | :---: |
| Sign up / log in | ✅ | ✅ | ✅ |
| Create and read items | ✅ | ✅ | ✅ |
| Update own items | ✅ | ✅ | ✅ |
| Update any item | ❌ | ✅ | ✅ |
| Delete items | ❌ | ✅ | ✅ |
| List users | ❌ | ❌ | ✅ |
| Change a user's role | ❌ | ❌ | ✅ |

| Role | How you get it |
| :--- | :--- |
| `staff` | Everybody starts here (signup or Google login) |
| `inventory_manager` | An admin promotes a user with `PATCH /users/{id}/role` (no code change needed) |
| `admin` | Only one: created from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` on every startup. Nobody can be promoted to admin |

### 7.3 Security measures in the code

| Measure | Where |
| :--- | :--- |
| Passwords stored as **bcrypt** hashes, never as plain text | `app/auth.py` |
| Password limited to 72 bytes (bcrypt reads only 72) | `app/schemas.py` |
| Same error for wrong email and wrong password (`401`) | `app/routers/auth.py` |
| App refuses to start without `SECRET_KEY`, or with the example value | `app/config.py` |
| Admin password must also be changed from the example value | `app/config.py` |
| Google login never merges into a password account (`409`) | `app/routers/auth.py` |
| Google token must have a verified email | `app/auth.py` |
| Duplicate signup at the same moment returns `409` (not `500`) | `app/routers/auth.py` |
| SQL injection: the ORM is used (no raw SQL); search characters are escaped | `app/routers/items.py` |
| Secrets live in `.env`, which is git-ignored and docker-ignored | `.gitignore`, `.dockerignore` |
| The container runs as a normal user, not root | `Dockerfile` |

---

## 8. Validation rules

Checked by Pydantic. Bad input returns `422` with the list of problems.

| Field | Rule |
| :--- | :--- |
| `name` (user, item) | 1–100 characters, spaces at the ends are removed |
| `email` | valid email format |
| `phone` | optional, 7–15 digits, optional `+` at the start |
| `password` | 8–64 characters, at most 72 bytes |
| `quantity` | integer **>= 0** (0 means out of stock) |
| `price` | number from 0.01 to 99999999.99 (stored with 2 decimals) |
| `page` / `limit` | `page` >= 1, `limit` from 1 to 100 |

---

## 9. Setup and run

### 9.1 Requirements

Docker Desktop (with Docker Compose). Python is needed only if you run the API or the tests without Docker.

### 9.2 Run everything with Docker (recommended)

```bash
# 1. Create your .env from the template
cp .env.example .env            # Windows: copy .env.example .env

# 2. Open .env and set:
#    SECRET_KEY      -> a long random string
#    ADMIN_EMAIL     -> your admin login email
#    ADMIN_PASSWORD  -> your admin password
#    (the app refuses to start if SECRET_KEY or ADMIN_PASSWORD still start with "change-me")

# 3. Build and start db + pgadmin + api
docker compose up --build
```

Then open **http://localhost:8000/docs**. The tables are created automatically (`alembic upgrade head` runs when the `web` container starts).

After you change code, `.env`, `requirements.txt` or the `Dockerfile`, run `docker compose up --build` again. To start with a fresh database: `docker compose down -v`. Stop with `Ctrl + C` or `docker compose down`.

### 9.3 Look at the data in pgAdmin

1. Open **http://localhost:5050** and log in with `admin@example.com` / `admin`.
2. *Add New Server* → **Connection** tab: host `db`, port `5432`, user `postgres`, password `postgres`, database `inventory_db`.
3. Open *Databases → inventory_db → Schemas → public → Tables* and view `users` and `items`.

Or use the terminal:
```bash
docker compose exec db psql -U postgres -d inventory_db -c "SELECT id, name, email, role FROM users;"
```

### 9.4 Run the API without Docker (database still in Docker)

```bash
docker compose up -d db                                   # PostgreSQL on localhost:5435
python -m venv venv
source venv/bin/activate                                  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

If PowerShell says "scripts are disabled", run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 9.5 Environment variables

| Variable | Required | Purpose |
| :--- | :---: | :--- |
| `SECRET_KEY` | yes | Signs the JWTs. App refuses to start if missing or still the example value |
| `ADMIN_EMAIL` | yes (for the admin) | Email of the one admin account |
| `ADMIN_PASSWORD` | yes (for the admin) | Password of the admin. Must not be the example value |
| `DATABASE_URL` | no | Defaults to `postgresql://postgres:postgres@localhost:5435/inventory_db`. Inside Docker, Compose sets it to the `db` service |
| `CORS_ORIGINS` | no | Websites allowed to call the API from a browser, comma separated. Default `http://localhost:3000` |
| `GOOGLE_CLIENT_ID` | no | Only needed for Sign in with Google |

Never commit `.env`. It is in `.gitignore`.

### 9.6 Google Sign-In setup (optional)

1. In [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) create an **OAuth client ID** of type **Web application**.
2. Under **Authorized JavaScript origins** add `http://localhost:8000`.
3. Copy the **Client ID** into `.env` as `GOOGLE_CLIENT_ID`. No client secret is needed, because the server only verifies Google's ID token.
4. Restart: `docker compose up -d --force-recreate`.
5. Open **http://localhost:8000/login**, click *Sign in with Google*, and copy the token it shows into Swagger (**Authorize**).

If the consent screen is in "Testing" mode, add your Google account under *Test users*. If `GOOGLE_CLIENT_ID` is empty, `/login` and `/auth/google` return `503`.

### 9.7 Five-minute demo

1. `docker compose up --build` → open `/docs`.
2. `POST /auth/signup`, then `POST /auth/login` → copy the token → **Authorize**.
3. `POST /items` a few times, then `GET /items?page=1&limit=2` (pagination) and `?search=key` (search).
4. `DELETE /items/{id}` as staff → **403**.
5. Log in as the admin → `GET /users` → `PATCH /users/{id}/role` to `inventory_manager`.
6. `DELETE /items/{id}` with the **same staff token** → **204** (the role comes from the database).
7. Look at the tables in pgAdmin, then run `pytest`.

---

## 10. Database migrations (Alembic)

The database structure is versioned with **Alembic**. The first migration (`alembic/versions/0001_create_users_and_items.py`) creates both tables. In Docker it runs by itself when the `web` container starts.

| What you want | Command |
| :--- | :--- |
| Create / update the tables | `alembic upgrade head` |
| Create a migration after changing `app/models.py` | `alembic revision --autogenerate -m "message"` |
| Go back one version | `alembic downgrade -1` |
| See the current version | `alembic current` |

Example: to add a `description` column to items, add it in `models.py`, run `alembic revision --autogenerate -m "add description"`, then `alembic upgrade head`. Old data is kept.

---

## 11. Tests

```bash
pip install -r requirements.txt
pytest
```

Expected result: **`3 passed`**.

- The tests run **without Docker** on a temporary SQLite file `test.db`, so they never touch your PostgreSQL data.
- No `.env` is needed: `tests/conftest.py` sets its own `SECRET_KEY`.
- `test.db` stays after the run. It is git-ignored; just ignore it.

| # | Test | What it proves |
| :-: | :--- | :--- |
| 1 | `test_signup_and_login` | Signup → 201, same email → 409, login gives a token, wrong password → 401 |
| 2 | `test_item_crud` | No token → 401, create / read / update, negative quantity → 422 |
| 3 | `test_roles` | Staff cannot delete (403), admin can (204) |

Concepts used: pytest fixtures (`client`, `staff_headers`, `admin_headers`).

---

## 12. Postman collection

Import [docs/postman_collection.json](docs/postman_collection.json) (*Import* → choose the file). Every request has test scripts (status codes and headers). Tokens and ids are saved automatically in **collection variables**.

| Folder | Requests |
| :--- | :--- |
| Auth | Signup · Login (staff + admin) · Google Login |
| Items | Create · List (pagination + search) · Get · Update · Delete (admin 204, staff 403, then 404) |
| Users (admin) | List users (admin 200, staff 403) · Change role (manager, then admin 422, then staff) |

How to run:

1. Collection variables: set `baseUrl` (default `http://localhost:8000`), and `adminEmail` / `adminPassword` **to match your `.env`**.
2. Run **Signup** and **Login** first. They save `token` and `adminToken`.
3. Run the **Items** requests in order, then the **Users** requests.
4. *Google Login* only works if you paste a real Google ID token into `googleIdToken`; skip it otherwise.

---

## 13. Design documents

| Document | Content |
| :--- | :--- |
| [REST_API_Design.md](docs/REST_API_Design.md) | Resources, URL structure, methods, request / response contracts, status codes |
| [GraphQL_Design.md](docs/GraphQL_Design.md) | GraphQL schema for the same app (design only) |
| [gRPC_Design.md](docs/gRPC_Design.md) | `inventory.proto` service definition (design only) |
| [Database_Design.md](docs/Database_Design.md) | ERD, table definitions, relationships, keys |
| [JWT_Design.md](docs/JWT_Design.md) | Token claims, flow, why the role comes from the database |

---
