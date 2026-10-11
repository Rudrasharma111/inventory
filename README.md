# Inventory Service

## Overview

This project is a RESTful backend built with **FastAPI** to manage inventory items. Users sign up or log in (email + password, or Google), get a **JWT token**, and use it to create, read, update and delete items. What a user may do depends on their **role**. Everything runs with one Docker command.

The application demonstrates real-world backend practices:

- JWT authentication and Google Sign-In
- Role-based access control (RBAC)
- PostgreSQL integration with SQLAlchemy and Alembic migrations
- Request validation with Pydantic
- Docker containerization (API + PostgreSQL + pgAdmin)
- Automatic API documentation
- Automated tests with pytest

## Key Features

### Authentication & Authorization
- User signup and login (email + password)
- Optional "Sign in with Google"
- JWT-based authentication (HS256, 60 minutes)
- Role-based access control: `staff`, `inventory_manager`, `admin`

### Inventory Management
- Create, read, update, delete items (CRUD)
- Pagination (`page`, `limit`) and search by name
- All logged-in users work on the same shared inventory

### User Management (admin only)
- List all users
- Promote a user to `inventory_manager` (or back to `staff`)

### Dockerized Setup
- `docker compose up --build` starts the database, pgAdmin and the API
- Tables are created automatically by Alembic

### API Documentation
- Swagger UI → `/docs`
- ReDoc → `/redoc`

### Testing
- Pytest test suite that runs without Docker (SQLite)
- Covers signup/login, item CRUD and role checks

## Project Goal

To build a clean, small, production-like backend using best practices:

- Separation of concerns (routers, schemas, models, security)
- Secure authentication (bcrypt, JWT, no secrets in code)
- Simple and readable code (about 460 lines in 10 files)
- Containerized deployment

## Tech Stack

| Category | Technology |
| :--- | :--- |
| Language | Python 3.11 |
| Framework | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (PyJWT, HS256) |
| Hashing | bcrypt |
| Social login | Google Sign-In (`google-auth`) |
| Containerization | Docker, Docker Compose, pgAdmin |
| Testing | Pytest, httpx |
| API client | Postman |

| URL | What you get |
| :--- | :--- |
| http://localhost:8000/docs | Swagger UI: try every endpoint in the browser |
| http://localhost:8000/redoc | ReDoc documentation |
| http://localhost:8000/health | Health check |
| http://localhost:8000/login | "Sign in with Google" page |
| http://localhost:5050 | pgAdmin: look at the database tables |

## Architecture Overview

```
Client → Middleware → Router → Dependencies (token + role check) → SQLAlchemy → PostgreSQL → Response
```

| Layer | File | Job |
| :--- | :--- | :--- |
| Routers | `app/routers/*.py` | Receive the request, run the logic, return the response |
| Schemas | `app/schemas/schemas.py` | Pydantic checks incoming data and shapes outgoing data |
| Security | `app/core/security.py` | Hash passwords, create and check JWTs, check roles |
| Models | `app/models/models.py` | Python classes that map to the tables |
| Database | `app/database/database.py` | Connection pool and one session per request |
| Config | `app/core/config.py` | Reads settings from `.env` |

## Project Structure

```
inventory-service/
├── app/
│   ├── main.py             # creates the app, CORS, middleware, creates the admin on startup
│   ├── core/
│   │   ├── config.py       # reads settings from .env
│   │   └── security.py     # password hashing, JWT, "who is logged in", role checks, Google check
│   ├── database/
│   │   └── database.py     # database engine and session (one session per request)
│   ├── models/
│   │   └── models.py       # the 2 tables: User, Item
│   ├── schemas/
│   │   └── schemas.py      # Pydantic models: validate requests, shape responses
│   ├── pages/
│   │   └── login_page.py   # small HTML page with the "Sign in with Google" button
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
├── M4ppt.pptx              # presentation
├── Dockerfile
├── docker-compose.yml      # db + pgadmin + web
├── alembic.ini
├── pytest.ini
├── requirements.txt        # all packages (app + pytest and httpx for tests)
├── .env.example            # template for your .env
└── README.md
```

## Local Setup

### 1. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```
If PowerShell says "scripts are disabled", run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your `.env`
```bash
cp .env.example .env              # Windows: copy .env.example .env
```
Open `.env` and set `SECRET_KEY`, `ADMIN_EMAIL` and `ADMIN_PASSWORD`. The app refuses to start while `SECRET_KEY` or `ADMIN_PASSWORD` still start with `change-me`.

### 4. Start the database (in Docker) and create the tables
```bash
docker compose up -d db           # PostgreSQL on localhost:5435
alembic upgrade head
```

### 5. Run the app
```bash
uvicorn app.main:app --reload
```

### 6. Open the API docs
http://localhost:8000/docs

## Docker Setup

Run everything (database + pgAdmin + API):
```bash
docker compose up --build
```
Then open **http://localhost:8000/docs**. The tables are created automatically (`alembic upgrade head` runs when the `web` container starts).

| What you want | Command |
| :--- | :--- |
| Run in background | `docker compose up -d` |
| Stop containers | `docker compose down` |
| Fresh database (deletes data) | `docker compose down -v` |
| After changing code, `.env`, `requirements.txt` or `Dockerfile` | `docker compose up --build` |

### Look at the data in pgAdmin
1. Open **http://localhost:5050** and log in with `admin@example.com` / `admin`.
2. *Add New Server* → **Connection** tab: host `db`, port `5432`, user `postgres`, password `postgres`, database `inventory_db`.
3. Open *Databases → inventory_db → Schemas → public → Tables*.

Or use the terminal:
```bash
docker compose exec db psql -U postgres -d inventory_db -c "SELECT id, name, email, role FROM users;"
```

## Environment Variables

| Variable | Required | Purpose |
| :--- | :---: | :--- |
| `SECRET_KEY` | yes | Signs the JWTs. App refuses to start if missing or still the example value |
| `ADMIN_EMAIL` | yes (for the admin) | Email of the one admin account |
| `ADMIN_PASSWORD` | yes (for the admin) | Password of the admin. Must not be the example value |
| `DATABASE_URL` | no | Defaults to `postgresql://postgres:postgres@localhost:5435/inventory_db`. Inside Docker, Compose sets it to the `db` service |
| `CORS_ORIGINS` | no | Websites allowed to call the API from a browser, comma separated. Default `http://localhost:3000` |
| `GOOGLE_CLIENT_ID` | no | Only needed for Sign in with Google |

Never commit `.env`. It is in `.gitignore` and `.dockerignore`.

## API Endpoints

Base URL: `http://localhost:8000` · Format: JSON · Interactive docs: `/docs`

Send the token as `Authorization: Bearer <access_token>`. In Swagger click **Authorize** and paste **only the token** (without the word `Bearer`).

### Health & Auth

| Method | Endpoint | Who | Description | Success | Errors |
| :--- | :--- | :--- | :--- | :-: | :--- |
| GET | `/health` | public | Health check | 200 | - |
| POST | `/auth/signup` | public | Register a user (role `staff`) | 201 | 409, 422 |
| POST | `/auth/login` | public | Log in, get a JWT | 200 | 401, 422 |
| POST | `/auth/google` | public | Log in with a Google ID token | 200 | 401, 409, 503 |

### Items

| Method | Endpoint | Who | Description | Success | Errors |
| :--- | :--- | :--- | :--- | :-: | :--- |
| POST | `/items` | any logged-in user | Create item | 201 | 401, 422 |
| GET | `/items?page=&limit=&search=` | any logged-in user | List items | 200 | 401, 422 |
| GET | `/items/{item_id}` | any logged-in user | Get one item | 200 | 401, 404 |
| PUT | `/items/{item_id}` | any logged-in user | Update item | 200 | 401, 404, 422 |
| DELETE | `/items/{item_id}` | manager, admin | Delete item | 204 | 401, 403, 404 |

### Users (admin only)

| Method | Endpoint | Description | Success | Errors |
| :--- | :--- | :--- | :-: | :--- |
| GET | `/users` | List users (never includes the password hash) | 200 | 401, 403 |
| PATCH | `/users/{user_id}/role` | Change a role to `inventory_manager` or `staff` | 200 | 400, 401, 403, 404, 422 |

### Examples

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

**PATCH `/users/{user_id}/role`**
```json
{ "role": "inventory_manager" }
```
Nobody can be made `admin`, and the admin's own role cannot be changed (`400`).

### Status codes used

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

Errors look like `{ "detail": "Item not found" }`. For `422`, `detail` lists the invalid fields. Every response has an `X-Process-Time` header (added by the middleware).

### Idempotency

| Method | Idempotent? | Why |
| :--- | :---: | :--- |
| GET | ✅ | Only reads |
| PUT | ✅ | Same body gives the same final state |
| DELETE | ✅ | The second call returns `404`, but nothing changes |
| PATCH (role) | ✅ | Sets a fixed role |
| POST | ❌ | Each call creates a new row |

## Authentication Flow

### Email + password
```
Client → POST /auth/login → JWT token
              ↓
Protected route → token validation → role check → access
```
1. `POST /auth/signup` hashes the password with bcrypt and saves the user with the role `staff`. A background task writes a "welcome message" to the log after the response is sent.
2. `POST /auth/login` finds the user by email and checks the password hash. If both are correct, it returns a JWT.
3. The client sends the JWT in the `Authorization: Bearer <token>` header with every request.

### Google Sign-In
1. The user opens `/login` and clicks "Sign in with Google".
2. Google gives the browser a Google ID token.
3. The browser sends `POST /auth/google` with `{ "id_token": "..." }`.
4. The API verifies the token (signature, expiry, our client id, verified email), then finds or creates the user (role `staff`).
5. The API returns our own JWT.

Rule: if the email already has a **password account**, Google login is rejected with `409`. Emails are not verified at signup, so merging could let a stranger who registered your email first stay inside your account.

### Life of a protected request
Example: `DELETE /items/5` with a token.

1. The middleware starts a timer and passes the request on.
2. `get_current_user` checks the token signature and expiry, then loads the user from the database.
3. `require_roles` checks that the role is `admin` or `inventory_manager`.
4. The item is deleted and the response is `204 No Content`.

## Roles and Permissions

The **role is read from the database on every request, not from the token**. So a role change works immediately and the user does not need to log in again.

| Action | staff | inventory_manager | admin |
| :--- | :---: | :---: | :---: |
| Sign up / log in | ✅ | ✅ | ✅ |
| Create, read and update items | ✅ | ✅ | ✅ |
| Delete items | ❌ | ✅ | ✅ |
| List users | ❌ | ❌ | ✅ |
| Change a user's role | ❌ | ❌ | ✅ |

| Role | How you get it |
| :--- | :--- |
| `staff` | Everybody starts here (signup or Google login) |
| `inventory_manager` | An admin promotes a user with `PATCH /users/{id}/role` (no code change needed) |
| `admin` | Only one: created from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` on every startup. Nobody can be promoted to admin |

## Database Design

PostgreSQL 15 with two tables. The ERD is in [docs/erd.svg](docs/erd.svg).

**`users`**

| Column | Type | Constraints |
| :--- | :--- | :--- |
| id | INTEGER | PRIMARY KEY (auto number) |
| name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| phone | VARCHAR(20) | NULL allowed |
| password_hash | VARCHAR(255) | NULL allowed (Google users have no password) |
| role | VARCHAR(20) | NOT NULL (`admin`, `inventory_manager`, `staff`) |

**`items`**

| Column | Type | Constraints |
| :--- | :--- | :--- |
| id | INTEGER | PRIMARY KEY (auto number) |
| name | VARCHAR(100) | NOT NULL, indexed (used by search) |
| quantity | INTEGER | NOT NULL (the API requires >= 0; 0 = out of stock) |
| price | NUMERIC(10,2) | NOT NULL (exact decimal, so money has no rounding errors) |
| created_by | INTEGER | NOT NULL, FOREIGN KEY → `users.id` |

One `user` creates many `items` (one-to-many). A user who has created items cannot be deleted from the database (the foreign key protects the items).

### Migrations (Alembic)
The first migration (`alembic/versions/0001_create_users_and_items.py`) creates both tables. In Docker it runs by itself when the `web` container starts.

| What you want | Command |
| :--- | :--- |
| Create / update the tables | `alembic upgrade head` |
| Create a migration after changing `app/models/models.py` | `alembic revision --autogenerate -m "message"` |
| Go back one version | `alembic downgrade -1` |
| See the current version | `alembic current` |

## Pagination

Pagination returns results in small chunks instead of loading everything at once.

```
GET /items?page=1&limit=5&search=key
```

| Query | Default | Rule |
| :--- | :--- | :--- |
| `page` | 1 | integer >= 1 |
| `limit` | 10 | integer from 1 to 100 |
| `search` | none | part of the item name, not case sensitive |

Internal logic: `skip = (page - 1) * limit` (page 1 → 0, page 2 → 10, page 3 → 20 when `limit=10`).

Example response:
```json
{
  "page": 1, "limit": 5, "total": 1,
  "items": [ { "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 2 } ]
}
```

## Validation Rules

Checked by Pydantic. Bad input returns `422` with the list of problems.

| Field | Rule |
| :--- | :--- |
| `name` (user, item) | 1–100 characters, spaces at the ends are removed |
| `email` | valid email format (saved in lowercase) |
| `phone` | optional, 7–15 digits, optional `+` at the start |
| `password` | 8–64 characters, at most 72 bytes |
| `quantity` | integer **>= 0** (0 means out of stock) |
| `price` | number from 0.01 to 99999999.99 (stored with 2 decimals) |
| `page` / `limit` | `page` >= 1, `limit` from 1 to 100 |

## Security Measures

| Measure | Where |
| :--- | :--- |
| Passwords stored as **bcrypt** hashes, never as plain text | `app/core/security.py` |
| Password limited to 72 bytes (bcrypt reads only 72) | `app/schemas/schemas.py` |
| Same error for wrong email and wrong password (`401`) | `app/routers/auth.py` |
| App refuses to start without `SECRET_KEY`, or with the example value | `app/core/config.py` |
| Admin password must also be changed from the example value | `app/core/config.py` |
| Google login never merges into a password account (`409`) | `app/routers/auth.py` |
| Google token must have a verified email | `app/core/security.py` |
| Duplicate signup at the same moment returns `409` (not `500`) | `app/routers/auth.py` |
| SQL injection: the ORM is used (no raw SQL); search characters are escaped | `app/routers/items.py` |
| Secrets live in `.env`, which is git-ignored and docker-ignored | `.gitignore`, `.dockerignore` |
| The container runs as a normal user, not root | `Dockerfile` |

## Google Sign-In Setup (optional)

1. In [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) create an **OAuth client ID** of type **Web application**.
2. Under **Authorized JavaScript origins** add `http://localhost:8000`.
3. Copy the **Client ID** into `.env` as `GOOGLE_CLIENT_ID`. No client secret is needed, because the server only verifies Google's ID token.
4. Restart: `docker compose up -d --force-recreate`.
5. Open **http://localhost:8000/login**, click *Sign in with Google*, and copy the token it shows into Swagger (**Authorize**).

If the consent screen is in "Testing" mode, add your Google account under *Test users*. If `GOOGLE_CLIENT_ID` is empty, `/login` and `/auth/google` return `503`.

## Testing

This project uses **Pytest** to check the core functionality.

```bash
pip install -r requirements.txt
pytest
```

Expected result: **`3 passed`**.

### Testing approach
- Uses FastAPI `TestClient` to send real API requests
- Runs **without Docker** on a temporary SQLite file `test.db`, so it never touches your PostgreSQL data
- No `.env` needed: `tests/conftest.py` sets its own `SECRET_KEY`
- Every test starts with a fresh, empty database (`client` fixture)
- `test.db` is git-ignored

### Test coverage

| # | Test | What it proves |
| :-: | :--- | :--- |
| 1 | `test_signup_and_login` | Signup → 201, same email → 409, login gives a token, wrong password → 401 |
| 2 | `test_item_crud` | No token → 401, create / read / update, negative quantity → 422 |
| 3 | `test_roles` | Staff cannot delete (403), admin can (204) |

Fixtures used: `client`, `staff_headers`, `admin_headers`.

Example flow: `Register → Login → Get Token → Access Protected Route`

## Postman Collection

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

## Five-Minute Demo

1. `docker compose up --build` → open `/docs`.
2. `POST /auth/signup`, then `POST /auth/login` → copy the token → **Authorize**.
3. `POST /items` a few times, then `GET /items?page=1&limit=2` (pagination) and `?search=key` (search).
4. `DELETE /items/{id}` as staff → **403**.
5. Log in as the admin → `GET /users` → `PATCH /users/{id}/role` to `inventory_manager`.
6. `DELETE /items/{id}` with the **same staff token** → **204** (the role comes from the database).
7. Look at the tables in pgAdmin, then run `pytest`.

## M4 Requirement Checklist

### Must submit

| Requirement | Status | Where |
| :--- | :---: | :--- |
| Git repository | ✅ | this repo |
| `REST_API_Design.md` | ✅ | [docs/REST_API_Design.md](docs/REST_API_Design.md) |
| FastAPI service | ✅ | `app/` |
| Auth | ✅ | `app/core/security.py`, `app/routers/auth.py` |
| PostgreSQL integration | ✅ | `app/database/database.py`, `app/models/models.py` (SQLAlchemy) |
| `GraphQL_Design.md` | ✅ | [docs/GraphQL_Design.md](docs/GraphQL_Design.md) |
| `gRPC_Design.md` | ✅ | [docs/gRPC_Design.md](docs/gRPC_Design.md) |
| `Database_Design.md` (ERD, tables, relationships, PK/FK) | ✅ | [docs/Database_Design.md](docs/Database_Design.md), [docs/erd.svg](docs/erd.svg) |
| `JWT_Design.md` | ✅ | [docs/JWT_Design.md](docs/JWT_Design.md) |
| Dockerfile | ✅ | `Dockerfile` (and `docker-compose.yml`) |
| README: API endpoints, setup, architecture, Postman, 3–5 tests | ✅ | this file |

### Stretch goals

| Goal | Status | Where |
| :--- | :---: | :--- |
| Pagination on a REST API | ✅ | `GET /items?page=1&limit=10` (also `search`) |
| Social login with Google | ✅ | `POST /auth/google` and the `/login` page |
| Role-based access | ✅ | 3 roles, checked by `require_roles(...)` |
| Swagger / OpenAPI docs | ✅ | `/docs` and `/redoc` (generated automatically) |

### Course topics used

| Topic | Where it is used |
| :--- | :--- |
| REST methods, status codes, idempotency | [API Endpoints](#api-endpoints) |
| Pydantic models and validators | `app/schemas/schemas.py` |
| SQLAlchemy ORM, queries, connection pooling | `app/models/models.py`, `app/database/database.py`, `app/routers/` |
| Database migrations | `alembic/` |
| JWT and OAuth login | `app/core/security.py` |
| Middleware | `add_process_time_header` in `app/main.py` |
| Background task | `send_welcome_message` in `app/routers/auth.py` |
| CORS | `CORSMiddleware` in `app/main.py` |
| dotenv | `app/core/config.py` |
| pytest fixtures | `tests/` |
| Docker + Docker Compose (PostgreSQL + pgAdmin) | `Dockerfile`, `docker-compose.yml` |

## Design Documents

| Document | Content |
| :--- | :--- |
| [REST_API_Design.md](docs/REST_API_Design.md) | Resources, URL structure, methods, request / response contracts, status codes |
| [GraphQL_Design.md](docs/GraphQL_Design.md) | GraphQL schema for the same app (design only) |
| [gRPC_Design.md](docs/gRPC_Design.md) | `inventory.proto` service definition (design only) |
| [Database_Design.md](docs/Database_Design.md) | ERD, table definitions, relationships, keys |
| [JWT_Design.md](docs/JWT_Design.md) | Token claims, flow, why the role comes from the database |

## Important Notes

- `created_by` in `items` points to the user who created the item.
- `price` is stored as `NUMERIC(10,2)`, not float, so money has no rounding errors.
- Pydantic v2 uses `ConfigDict(from_attributes=True)` to turn database rows into responses.
- Docker only installs `requirements.txt`; it does not generate it.
- The `tests/` folder is not copied into the Docker image (see `.dockerignore`); run `pytest` on your machine.

## Final Status

- All 3 tests passing
- Secure authentication (bcrypt + JWT + optional Google login)
- Role-based inventory management
- Dockerized backend with migrations
- Clean, small codebase