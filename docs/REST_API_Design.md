# REST API Design Specification

This document provides the complete API specification and architectural design for the Inventory Management Service.

---

## 1. Resource Structure
The API strictly follows RESTful naming conventions. Resources are represented as plural nouns, lowercase, and without verbs. 

* **`auth`**: Handles user authentication, registration, and Google OAuth.
* **`items`**: Represents the inventory products. Each item is linked to the user who created it.
* **`users`**: Represents system users. Used strictly for administrative management (role assignments).
* **`health`**: A simple resource to check server status.

---

## 2. API URL Structure & Method
The action is defined by the HTTP method rather than the URL itself.

| Resource | Action | Method | API URL | Access Level |
| :--- | :--- | :--- | :--- | :--- |
| **auth** | Sign Up | POST | `/auth/signup` | Public |
| **auth** | Password Login | POST | `/auth/login` | Public |
| **auth** | Google Login | POST | `/auth/google` | Public |
| **items** | List Items | GET | `/items?page=1&limit=10` | Logged In |
| **items** | Read One Item | GET | `/items/{item_id}` | Logged In |
| **items** | Create Item | POST | `/items` | Logged In |
| **items** | Update Item | PUT | `/items/{item_id}` | Logged In |
| **items** | Delete Item | DELETE | `/items/{item_id}` | `inventory_manager` or `admin` |
| **users** | List Users | GET | `/users` | `admin` only |
| **users** | Change Role | PATCH | `/users/{user_id}/role`| `admin` only |
| **health** | Server Status | GET | `/health` | Public |

---

## 3. Request / Response Contract
All data is exchanged in `application/json` format. 

### A. Auth Contracts
* **POST `/auth/signup`**
  * **Request:** `{ "name": "Rahul", "email": "user@example.com", "phone": "+919876543210", "password": "pass" }`
  * **Response (201):** `{ "id": 1, "name": "Rahul", "email": "user@example.com", "phone": "+919876543210", "role": "staff" }`
* **POST `/auth/login`**
  * **Request:** `{ "email": "user@example.com", "password": "pass" }`
  * **Response (200):** `{ "access_token": "<jwt>", "token_type": "bearer", "role": "staff" }`

### B. Items Contracts
* **POST `/items` & PUT `/items/{item_id}`**
  * **Request:** `{ "name": "Keyboard", "quantity": 10, "price": 49.99 }`
  * **Validation:** `name`: 1-100 chars, `quantity`: >= 0, `price`: 0.01 to 99999999.99.
  * **Response (201/200):** `{ "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "created_by": 1 }`
* **GET `/items`**
  * **Response (200):** `{ "page": 1, "limit": 10, "total": 25, "items": [ { ...item_data... } ] }`
* **DELETE `/items/{item_id}`**
  * **Response (204):** Empty body.

### C. Users Contract
* **PATCH `/users/{user_id}/role`**
  * **Request:** `{ "role": "inventory_manager" }`
  * **Response (200):** Returns updated user object. (400 Bad Request if trying to change admin's role).

---

## 4. FastAPI Service
The backend engine is powered by FastAPI, leveraging its modern asynchronous capabilities.

* **Modularity:** Routes are divided into `auth.py`, `items.py`, and `users.py` and connected via `app.include_router()`.
* **Validation:** Pydantic models (Schemas) enforce strict data types and constraints before requests hit the business logic.
* **Middleware:**
  * **CORS:** Uses `CORSMiddleware` to allow specific frontend origins safely.
  * **Performance Tracking:** A custom HTTP middleware calculates process time and appends `X-Process-Time` (in ms) to every response header.
* **Lifespan Manager:** Ensures the system always has an Admin account by reading `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env` on server startup.

---

## 5. Auth
Authentication is completely stateless, utilizing JSON Web Tokens (JWT).

* **JWT Configuration:** Uses `PyJWT` with `HS256` signature. `SECRET_KEY` is loaded securely from `.env`. Tokens expire in 60 minutes.
* **Transmission:** Tokens must be sent in the header as `Authorization: Bearer <access_token>`.
* **Token Claims:** Contains `sub` (User ID), `email`, `role`, `iat`, and `exp`.
* **Security & Roles Design:** 
  * Although the token contains the `role` for client convenience, **the server always fetches the role from the database** during requests. This ensures immediate effect if a user is promoted, demoted, or deleted.
  * **Roles:** 
    * `staff`: Default for all signups. Read/Write items.
    * `inventory_manager`: Read/Write/Delete items.
    * `admin`: Manage users and roles.
  * Passwords are encrypted with `bcrypt`. Google OAuth bypasses passwords (leaves password_hash NULL).

---

## 6. PostgreSQL Integration
The database layer uses PostgreSQL 15, managed via SQLAlchemy (ORM) and Alembic (Migrations).

* **`users` Table:**
  * `id`: Primary Key
  * `email`: VARCHAR(255) - Enforced as **UNIQUE** and **Indexed** for high-speed login queries.
  * `password_hash`: Nullable (to support Google OAuth users).
* **`items` Table:**
  * `name`: VARCHAR(100) - **Indexed** to support fast text-based searching without performance bottlenecks.
  * `price`: `NUMERIC(10,2)` - Used instead of Float to guarantee exact precision and avoid rounding errors for currency.
* **Relationships:**
  * **One-to-Many:** One user creates many items (`items.created_by` -> `users.id`).
  * **Data Integrity:** The foreign key strictly prevents deleting a user if they have created items, avoiding orphaned database records.