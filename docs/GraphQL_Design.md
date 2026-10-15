# GraphQL Design

Project: **Inventory Service** (FastAPI + PostgreSQL + JWT)
Endpoint: `POST http://localhost:8000/graphql` | Format: JSON | Browser tool: GraphiQL at `/graphql`

This is a **design file**. The running API is REST. This file shows how the **same app** looks as a GraphQL API, with the **same JWT**, the **same roles**, the **same validation rules** and the **same PostgreSQL tables** (`users`, `items`).

---

## 1. What is GraphQL? (short)

GraphQL is a way to ask a server for data using a **query language**.

1. **One endpoint.** Everything goes to `POST /graphql`. REST has many URLs, GraphQL has one.
2. **The client chooses the fields.** If the client only needs `id` and `name`, it asks only for those. No extra data (no over-fetching).
3. **One call for related data.** An item and its creator can come in one request.
4. **Strongly typed schema.** The server publishes a schema (SDL). The schema is the contract, like `openapi.json` in REST.
5. **Two kinds of operations.** `query` reads data. `mutation` changes data (create, update, delete). A third kind, `subscription`, is for live updates and is not used here.

---

## 2. Architecture flow (block diagram)

### 2.1 Big picture

```
 +-----------------+      POST /graphql (JSON)       +---------------------------+
 |  Client         |  { "query": "...",              |  FastAPI app (port 8000)  |
 |  Postman /      |    "variables": {...} }         |                           |
 |  GraphiQL /     | ------------------------------> |  /graphql  (Strawberry)   |
 |  Frontend       |  Authorization: Bearer <JWT>    |  /items /users /auth ...  |
 |                 | <------------------------------ |  (REST keeps working)     |
 +-----------------+   { "data": ..., "errors": ... }+-------------+-------------+
                                                                   |
                                                                   v
                                                     +---------------------------+
                                                     |  PostgreSQL 15 (port 5435)|
                                                     |  tables: users, items     |
                                                     +---------------------------+
```

### 2.2 One request inside the code (example: `createItem`)

```
 Client
   |  POST /graphql  + JWT
   |  mutation { createItem(input: {name:"Keyboard", quantity:10, price:49.99}) { id } }
   v
+----------------------------------------------------------------------+
| 1. CORS (main.py)                                                    |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 2. GraphQLRouter (app/graphql/router.py)  ->  parses the query text  |
|    checks it against the schema (unknown field -> error)             |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 3. Context (app/graphql/context.py)                                  |
|    reads the Bearer token, loads the user from the DB (or None)      |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 4. Permission class (IsAuthenticated / IsManagerOrAdmin / IsAdmin)   |
|    UNAUTHENTICATED or FORBIDDEN error if not allowed                 |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 5. Resolver create_item()                                            |
|    validate with the same Pydantic ItemIn as REST                    |
|    Item(..., created_by=user.id) -> db.add -> db.commit             |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 6. SQLAlchemy model Item -> PostgreSQL INSERT                        |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 7. Only the requested fields are returned, HTTP 200                  |
|    { "data": { "createItem": { "id": "1" } } }                       |
+----------------------------------------------------------------------+
```

---

## 3. Schema (SDL)

```graphql
# ---------- Enums ----------
enum Role {
  ADMIN
  INVENTORY_MANAGER
  STAFF
}

# Roles an admin is allowed to give (same as REST: "admin" cannot be assigned)
enum AssignableRole {
  INVENTORY_MANAGER
  STAFF
}

# ---------- Output types ----------
type User {
  id: ID!
  name: String!
  email: String!
  role: Role!
}

# Small public view of a user, so a normal user cannot see other people's email
type Creator {
  id: ID!
  name: String!
}

type Item {
  id: ID!
  name: String!
  quantity: Int!
  price: Float!
  createdBy: ID!
  creator: Creator!     # related data in the same call (not possible in one REST call)
}

type ItemPage {
  page: Int!
  limit: Int!
  total: Int!
  items: [Item!]!
}

type AuthPayload {
  accessToken: String!
  tokenType: String!    # always "bearer"
  role: Role!
}

type DeleteItemPayload {
  id: ID!
  deleted: Boolean!
}

type Health {
  status: String!
}

# ---------- Input types ----------
input SignupInput {
  name: String!         # 1-100 characters
  email: String!        # valid email
  password: String!     # 8-64 characters
}

input LoginInput {
  email: String!
  password: String!
}

input ItemInput {
  name: String!         # 1-100 characters
  quantity: Int!        # >= 0
  price: Float!         # 0.01 to 99999999.99
}

# ---------- Operations ----------
type Query {
  health: Health!
  me: User!                                                   # the logged-in user
  item(id: ID!): Item                                         # null + NOT_FOUND error if missing
  items(page: Int = 1, limit: Int = 10, createdBy: ID): ItemPage!   # paginated (limit 1-100)
  users: [User!]!                                             # admin only
}

type Mutation {
  signup(input: SignupInput!): User!
  login(input: LoginInput!): AuthPayload!
  googleLogin(idToken: String!): AuthPayload!

  createItem(input: ItemInput!): Item!
  updateItem(id: ID!, input: ItemInput!): Item!
  deleteItem(id: ID!): DeleteItemPayload!

  changeUserRole(userId: ID!, role: AssignableRole!): User!   # admin only
}
```

Notes:
- `ID` is sent as a string in JSON (`"id": "1"`), the database still stores an integer.
- The `Role` enum names are upper case. In the database the values stay lower case (`staff`, `inventory_manager`, `admin`), the enum maps between them.
- SDL cannot express "at least 8 characters" or "price between 0.01 and 99999999.99". These limits are checked in the resolver with the same Pydantic classes as REST (`SignupRequest`, `ItemIn`), so REST and GraphQL always use the same rules.
- `items(createdBy: ID)` returns only the items created by one user (for example `createdBy: "5"`).

---

## 4. Auth and roles

The JWT is **exactly the same** as in REST (see `JWT_Design.md`).

1. Call the `login` (or `googleLogin`) mutation. It is public and returns `accessToken`.
2. Send the token in the HTTP header of every later request: `Authorization: Bearer <accessToken>`. The header goes on the HTTP request, not inside the query.
3. The server checks the signature and expiry, then **loads the user from the database** with `sub`. The role is taken from the database, not from the token.

| Operation | Who can call |
| :--- | :--- |
| `health`, `signup`, `login`, `googleLogin` | public |
| `me`, `item`, `items`, `createItem`, `updateItem` | any logged-in user |
| `deleteItem` | `INVENTORY_MANAGER`, `ADMIN` |
| `users`, `changeUserRole` | `ADMIN` |

Rules kept from REST:
- Signup and Google login always create a `STAFF` user.
- The role of an admin cannot be changed.
- A password account cannot be opened with Google login (`CONFLICT`).

---

## 5. Request and response examples

All examples are `POST /graphql` with `Content-Type: application/json`.

### 5.1 `login` (public)

Request body:
```json
{
  "query": "mutation Login($input: LoginInput!) { login(input: $input) { accessToken tokenType role } }",
  "variables": { "input": { "email": "user@example.com", "password": "password123" } }
}
```
Response (HTTP 200):
```json
{ "data": { "login": { "accessToken": "eyJhbGciOi...", "tokenType": "bearer", "role": "STAFF" } } }
```

### 5.2 `createItem` (logged in)

```graphql
mutation {
  createItem(input: { name: "Keyboard", quantity: 10, price: 49.99 }) {
    id
    name
    createdBy
  }
}
```
Response:
```json
{ "data": { "createItem": { "id": "1", "name": "Keyboard", "createdBy": "2" } } }
```

### 5.3 `items` with pagination and the creator (one call)

```graphql
query {
  items(page: 1, limit: 2) {
    page
    limit
    total
    items { id name price creator { name } }
  }
}
```
Response:
```json
{
  "data": {
    "items": {
      "page": 1, "limit": 2, "total": 7,
      "items": [
        { "id": "1", "name": "Keyboard", "price": 49.99, "creator": { "name": "Rudra" } },
        { "id": "2", "name": "Mouse",    "price": 19.5,  "creator": { "name": "Rudra" } }
      ]
    }
  }
}
```
With REST this needs two kinds of calls (`GET /items`, then the user data). Here it is one call, and the client asked only for the fields it needs.

### 5.4 Items created by one user

```graphql
query {
  items(createdBy: "5", page: 1, limit: 10) { total items { id name quantity } }
}
```

### 5.5 `updateItem`, `deleteItem`

```graphql
mutation { updateItem(id: "1", input: { name: "Keyboard", quantity: 8, price: 45 }) { id quantity price } }
mutation { deleteItem(id: "1") { id deleted } }
```
`deleteItem` needs `INVENTORY_MANAGER` or `ADMIN`.

### 5.6 `changeUserRole` (admin)

```graphql
mutation { changeUserRole(userId: "3", role: INVENTORY_MANAGER) { id name role } }
```
Response:
```json
{ "data": { "changeUserRole": { "id": "3", "name": "Asha", "role": "INVENTORY_MANAGER" } } }
```

---

## 6. Errors

GraphQL always answers with **HTTP 200** when the query itself was understood. A problem is reported in an `errors` list, and the failed field is `null`. The machine-readable reason is in `extensions.code`.

```json
{
  "data": null,
  "errors": [
    {
      "message": "Your role is not allowed to do this",
      "path": ["deleteItem"],
      "extensions": { "code": "FORBIDDEN" }
    }
  ]
}
```

Mapping from REST status codes:

| REST | GraphQL `extensions.code` | Example |
| :-: | :--- | :--- |
| 401 | `UNAUTHENTICATED` | Token missing, bad or expired; wrong email or password |
| 403 | `FORBIDDEN` | A `STAFF` user calls `deleteItem` |
| 404 | `NOT_FOUND` | `item(id: "999")`, `changeUserRole` on a missing user |
| 409 | `CONFLICT` | Email already registered; Google login for a password account |
| 400, 422 | `BAD_USER_INPUT` | `price: 0`, `quantity: -1`, changing the admin's role |
| 503 | `SERVICE_UNAVAILABLE` | Google login is not configured |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected server error |

Validation error example (`price: 0`):
```json
{
  "data": null,
  "errors": [
    {
      "message": "price: Input should be greater than or equal to 0.01",
      "path": ["createItem"],
      "extensions": { "code": "BAD_USER_INPUT" }
    }
  ]
}
```

If the query has a wrong field name or a wrong type (for example `items(page: "one")`), the server rejects it before running any code with the code `GRAPHQL_VALIDATION_FAILED`.

---

## 7. REST to GraphQL map

| # | REST | GraphQL |
| :-: | :--- | :--- |
| 1 | `GET /health` | `query { health { status } }` |
| 2 | `POST /auth/signup` | `mutation signup(input)` |
| 3 | `POST /auth/login` | `mutation login(input)` |
| 4 | `POST /auth/google` | `mutation googleLogin(idToken)` |
| 5 | `POST /items` | `mutation createItem(input)` |
| 6 | `GET /items?page=&limit=` | `query items(page, limit, createdBy)` |
| 7 | `GET /items/{item_id}` | `query item(id)` |
| 8 | `PUT /items/{item_id}` | `mutation updateItem(id, input)` |
| 9 | `DELETE /items/{item_id}` | `mutation deleteItem(id)` |
| 10 | `GET /users` | `query users` |
| 11 | `PATCH /users/{user_id}/role` | `mutation changeUserRole(userId, role)` |
| 12 | (none, uses the token) | `query me` |

---

## 8. Example: how to build ONE endpoint in GraphQL (`createItem`)

Library: **Strawberry** (works well with FastAPI).

### Step 1: install
```bash
pip install "strawberry-graphql[fastapi]"
```
Add `strawberry-graphql[fastapi]` to `requirements.txt`.

### Step 2: types (`app/graphql/types.py`)
```python
import strawberry
from app.models.models import Item

@strawberry.type
class ItemType:
    id: strawberry.ID
    name: str
    quantity: int
    price: float
    created_by: strawberry.ID          # shown as createdBy in the schema

    @staticmethod
    def from_model(item: Item) -> "ItemType":
        return ItemType(
            id=strawberry.ID(str(item.id)),
            name=item.name,
            quantity=item.quantity,
            price=float(item.price),
            created_by=strawberry.ID(str(item.created_by)),
        )

@strawberry.input
class ItemInput:
    name: str
    quantity: int
    price: float
```

### Step 3: context (who is calling) (`app/graphql/context.py`)
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.security import get_optional_user
from app.database.database import get_db

async def get_context(db: Session = Depends(get_db), user=Depends(get_optional_user)):
    return {"db": db, "user": user}
```
`get_optional_user` (in `app/core/security.py`) is the same as `get_current_user`, but it returns `None` instead of raising 401. This is needed because `login` and `signup` must work without a token.

### Step 4: permissions (`app/graphql/permissions.py`)
```python
from strawberry.permission import BasePermission

class IsAuthenticated(BasePermission):
    message = "Not authenticated"
    error_extensions = {"code": "UNAUTHENTICATED"}

    def has_permission(self, source, info, **kwargs) -> bool:
        return info.context["user"] is not None

class IsManagerOrAdmin(BasePermission):
    message = "Your role is not allowed to do this"
    error_extensions = {"code": "FORBIDDEN"}

    def has_permission(self, source, info, **kwargs) -> bool:
        user = info.context["user"]
        return user is not None and user.role in ("admin", "inventory_manager")

class IsAdmin(BasePermission):
    message = "Your role is not allowed to do this"
    error_extensions = {"code": "FORBIDDEN"}

    def has_permission(self, source, info, **kwargs) -> bool:
        user = info.context["user"]
        return user is not None and user.role == "admin"
```

### Step 5: the resolver (`app/graphql/schema.py`)
```python
import strawberry
from graphql import GraphQLError
from pydantic import ValidationError
from strawberry.types import Info
from app.graphql.permissions import IsAuthenticated
from app.graphql.types import ItemInput, ItemType
from app.models.models import Item
from app.schemas.schemas import ItemIn

@strawberry.type
class Mutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def create_item(self, info: Info, input: ItemInput) -> ItemType:
        db, user = info.context["db"], info.context["user"]

        try:                                    # same rules as REST
            data = ItemIn(name=input.name, quantity=input.quantity, price=input.price)
        except ValidationError as e:
            err = e.errors()[0]
            raise GraphQLError(f"{err['loc'][0]}: {err['msg']}",
                               extensions={"code": "BAD_USER_INPUT"})

        item = Item(**data.model_dump(), created_by=user.id)
        db.add(item)
        db.commit()
        db.refresh(item)
        return ItemType.from_model(item)

@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "ok"

schema = strawberry.Schema(query=Query, mutation=Mutation)
```
The other operations are written the same way: check permission, validate, use the same SQLAlchemy code as the REST router, convert to the output type.

### Step 6: mount it in `app/main.py`
```python
from strawberry.fastapi import GraphQLRouter
from app.graphql.context import get_context
from app.graphql.schema import schema

app.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")
```

### Step 7: test
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"query":"mutation { createItem(input:{name:\"Keyboard\",quantity:10,price:49.99}) { id name } }"}'
```
In Postman: new request, method `POST`, body type **GraphQL**, URL `http://localhost:8000/graphql`, and the token on the Authorization tab (Bearer Token).

---

## 9. Things to be careful about

| Topic | What to do |
| :--- | :--- |
| **N+1 problem** | The field `Item.creator` runs one query per item if written naively (10 items = 10 user queries). Use a **DataLoader**, which collects all ids and runs one query: `SELECT ... FROM users WHERE id IN (...)`. |
| **Pagination limit** | `limit` is limited to 1-100 (same as REST), so nobody can ask for the whole table. |
| **Deep or heavy queries** | Set a maximum query depth and complexity, so a client cannot send a very deep nested query. |
| **Introspection** | Useful in development (GraphiQL, Postman). Turn it off in production. |
| **Private data** | `Creator` shows only `id` and `name`. Email and role are only in `User`, which only `me` and `users` (admin) return. |
| **Caching** | Everything is `POST /graphql`, so normal HTTP caching of `GET` does not work as in REST. |
| **Sync database code** | The project uses a synchronous SQLAlchemy session. For a small app this is fine. For heavy load use an async driver, or run the database code in a thread pool. |
| **Rate limiting** | Add a limit per user or IP in front of `/graphql`, especially for `login`. |

---

## 10. Why GraphQL (and when)

Good fit:
- Web or mobile apps where different screens need different fields from the same data.
- Dashboards that need several related things (items + creator + totals) in one call.
- Frontend teams that change what they need often, without waiting for new backend endpoints.

Not the best fit:
- Simple CRUD with fixed responses (REST is simpler and `GET` is easy to cache).
- File upload and download (REST is simpler).
- Fast internal calls between backend services (gRPC is better).

| Point | REST (built) | GraphQL (this design) |
| :--- | :--- | :--- |
| URLs | Many | One: `/graphql` |
| Who chooses the response fields | Server | Client |
| Related data | Several calls | One call |
| Errors | HTTP status (401, 404 ...) | HTTP 200 + `errors` list with `extensions.code` |
| Contract | OpenAPI / Swagger | Schema (SDL), GraphiQL |
| Caching | Easy | Harder |
| Auth, roles, validation, database | JWT, 3 roles, Pydantic, PostgreSQL | **Same** |