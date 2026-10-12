# GraphQL API Design Specification

This document provides the GraphQL architecture and API specification for the Inventory Management Service. It enforces the exact same business rules, authentication logic, and database operations as the REST API, but uses a single flexible endpoint.

---

## 1. Resource Structure & Endpoint
Unlike REST which uses multiple URLs for different resources, GraphQL operates through a single endpoint. The action is determined by the Query (for reading) or Mutation (for writing).

* **Endpoint:** `POST /graphql`
* **Format:** `application/json`
* **Public Operations:** `signup`, `login`, `googleLogin`, `health`.
* **Secured Operations:** All other operations require a JWT token.

---

## 2. API Schema & Operations (REST vs GraphQL)

Instead of HTTP methods (GET/POST/PUT/DELETE), GraphQL uses a strongly typed schema.

| Operation Type | Name | Equivalent REST | Access Level |
| :--- | :--- | :--- | :--- |
| **Query** | `health` | `GET /health` | Public |
| **Mutation** | `signup` | `POST /auth/signup` | Public |
| **Mutation** | `login` | `POST /auth/login` | Public |
| **Mutation** | `googleLogin`| `POST /auth/google` | Public |
| **Query** | `items` | `GET /items?page&limit` | Logged In |
| **Query** | `item(id)` | `GET /items/{id}` | Logged In |
| **Mutation** | `createItem` | `POST /items` | Logged In |
| **Mutation** | `updateItem` | `PUT /items/{id}` | Logged In |
| **Mutation** | `deleteItem` | `DELETE /items/{id}`| `inventory_manager` / `admin` |
| **Query** | `users` | `GET /users` | `admin` only |
| **Mutation** | `updateUserRole`| `PATCH /users/{id}/role`| `admin` only |

---

## 3. Request / Response Contract

All GraphQL responses return **HTTP 200 OK**. Errors are handled inside the JSON response body under the `errors` array, using custom extension codes.

### A. Auth Contracts
* **Signup (Mutation)**
  * **Input:** `{ name: "Rudra", email: "user@example.com", password: "pass" }`
  * **Returns:** `User` object (Role defaults to `STAFF`).
* **Login (Mutation)**
  * **Input:** `{ email: "user@example.com", password: "pass" }`
  * **Returns:** `AuthPayload` containing `accessToken`, `tokenType`, and `role`.

### B. Items Contracts (The GraphQL Advantage)
* **Read Items (Query)**
  * *Advantage over REST:* You can fetch the item AND its creator's details in a single request (no over-fetching/under-fetching).
  * **Query:**
    ```graphql
    query {
      items(page: 1, limit: 10) {
        total
        items { id name price creator { name } }
      }
    }
    ```
* **Create Item (Mutation)**
  * **Input:** `ItemInput` `{ name: "Keyboard", quantity: 10, price: 49.99 }`
  * **Returns:** `Item` object.

### C. Error Handling (Extensions Code)
If a rule is violated, GraphQL returns standard codes mapped directly from REST concepts:
* `UNAUTHENTICATED` (REST 401) - Missing or expired token.
* `FORBIDDEN` (REST 403) - Role not allowed (e.g., Staff trying to delete).
* `NOT_FOUND` (REST 404) - Item or user does not exist.
* `CONFLICT` (REST 409) - Email already registered.
* `BAD_USER_INPUT` (REST 422) - Invalid Pydantic validation (e.g., negative price).

---

## 4. FastAPI Service Integration
The backend engine leverages the exact same service layer as REST.
* **Library:** `strawberry-graphql` is mounted on the FastAPI app at `/graphql`.
* **Context Injection:** The exact same JWT verification function (`get_current_user`) used in REST is injected into the GraphQL Context.
* **Shared Logic:** The business rules (e.g., checking if an email is duplicate) live in a shared service layer, meaning REST and GraphQL execute the exact same Python functions under the hood.

---

## 5. Auth
Authentication remains completely stateless and identical to the REST implementation.
* **JWT Configuration:** Uses `PyJWT` (`HS256` signature, 60-minute expiry).
* **Transmission:** Tokens must be sent in the HTTP headers: `Authorization: Bearer <access_token>`.
* **Dynamic Roles:** Even though the token contains the user's role, the GraphQL resolver strictly reads the role from the PostgreSQL database during the request to ensure immediate application of promotions or demotions.

---

## 6. PostgreSQL Integration
The database layer (PostgreSQL 15 + SQLAlchemy) remains unchanged.
* **Models:** GraphQL types (`Item`, `User`) map directly to the SQLAlchemy ORM models.
* **Data Integrity:** `items.created_by` references `users.id`. Users who have created items cannot be deleted. 
* **Precision:** Prices are handled as `NUMERIC(10,2)` in the DB and mapped to `Float` in GraphQL.