# GraphQL Design

Project: **Inventory Service** (FastAPI + PostgreSQL + JWT)
Endpoint: `POST /graphql` (one URL for everything) | Format: JSON

This is a **design file**. The running API is REST. GraphQL here describes the **same app**: same JWT, same roles, same validation rules, same tables (`users`, `items`).

---

## 1. What is GraphQL?

- **One endpoint.** All calls go to `POST /graphql`. REST has many URLs.
- **The client chooses the fields.** If the client needs only `name` and `price`, it asks only for those.
- **Two kinds of calls.** `query` = read data (like GET). `mutation` = change data (like POST, PUT, DELETE).
- **Schema.** A list of types. It is the contract between client and server.

---

## 2. How a request flows

```
Client (Postman / GraphiQL)
   |  POST /graphql   +   Authorization: Bearer <JWT>
   v
FastAPI  ->  GraphQL router  ->  check token & role  ->  resolver
                                                            |
                                                            v
                                                      SQLAlchemy -> PostgreSQL
   ^
   |  HTTP 200   { "data": { ... } }   or   { "errors": [ ... ] }
```

---

## 3. Schema

```graphql
enum Role { ADMIN  INVENTORY_MANAGER  STAFF }

type User {
  id: ID!
  name: String!
  email: String!
  role: Role!
}

type Item {
  id: ID!
  name: String!
  quantity: Int!
  price: Float!
  createdBy: ID!
}

type ItemPage {
  page: Int!
  limit: Int!
  total: Int!
  items: [Item!]!
}

type AuthPayload {
  accessToken: String!
  tokenType: String!
  role: Role!
}

input SignupInput { name: String!  email: String!  password: String! }
input LoginInput  { email: String!  password: String! }
input ItemInput   { name: String!  quantity: Int!  price: Float! }

type Query {
  me: User!
  item(id: ID!): Item
  items(page: Int = 1, limit: Int = 10, createdBy: ID): ItemPage!
  users: [User!]!
}

type Mutation {
  signup(input: SignupInput!): User!
  login(input: LoginInput!): AuthPayload!
  googleLogin(idToken: String!): AuthPayload!
  createItem(input: ItemInput!): Item!
  updateItem(id: ID!, input: ItemInput!): Item!
  deleteItem(id: ID!): Boolean!
  changeUserRole(userId: ID!, role: Role!): User!
}
```

Rules (same as REST):
- `name`: 1-100 characters. `quantity`: 0 or more. `price`: more than 0. `password`: 8-64 characters.
- `changeUserRole` can set only `STAFF` or `INVENTORY_MANAGER`. The role of an admin cannot be changed.
- `items` is paginated, `limit` is 1-100. `createdBy` is optional and shows only the items of one user.

---

## 4. Operations, access and REST equivalent

| Operation | Type | Who can call | REST equivalent |
| :--- | :--- | :--- | :--- |
| `signup` | mutation | public | `POST /auth/signup` |
| `login` | mutation | public | `POST /auth/login` |
| `googleLogin` | mutation | public | `POST /auth/google` |
| `me` | query | any logged-in user | (from the token) |
| `items` | query | any logged-in user | `GET /items?page=&limit=` |
| `item` | query | any logged-in user | `GET /items/{id}` |
| `createItem` | mutation | any logged-in user | `POST /items` |
| `updateItem` | mutation | any logged-in user | `PUT /items/{id}` |
| `deleteItem` | mutation | inventory_manager, admin | `DELETE /items/{id}` |
| `users` | query | admin | `GET /users` |
| `changeUserRole` | mutation | admin | `PATCH /users/{id}/role` |

---

## 5. Auth

Same JWT as REST (see `JWT_Design.md`).
1. Call `login` (or `googleLogin`). It returns `accessToken`.
2. Send it on every later call in the HTTP header: `Authorization: Bearer <accessToken>`.
3. The server checks the token and loads the user from the database. The role comes from the database.

---

## 6. Examples

### login
```json
{
  "query": "mutation { login(input: {email: \"user@example.com\", password: \"password123\"}) { accessToken role } }"
}
```
Response:
```json
{ "data": { "login": { "accessToken": "eyJhbGciOi...", "role": "STAFF" } } }
```

### createItem (needs token)
```graphql
mutation {
  createItem(input: { name: "Keyboard", quantity: 10, price: 49.99 }) { id name createdBy }
}
```
Response:
```json
{ "data": { "createItem": { "id": "1", "name": "Keyboard", "createdBy": "2" } } }
```

### items with pagination (client asks only for what it needs)
```graphql
query {
  items(page: 1, limit: 2) { page limit total items { id name price } }
}
```
Response:
```json
{
  "data": {
    "items": {
      "page": 1, "limit": 2, "total": 7,
      "items": [
        { "id": "1", "name": "Keyboard", "price": 49.99 },
        { "id": "2", "name": "Mouse", "price": 19.5 }
      ]
    }
  }
}
```

### Items created by one user
```graphql
query { items(createdBy: "5") { total items { id name } } }
```

---

## 7. Errors

GraphQL answers with HTTP 200. A problem is shown in an `errors` list with a code.

```json
{
  "data": null,
  "errors": [ { "message": "Not authenticated", "extensions": { "code": "UNAUTHENTICATED" } } ]
}
```

| REST | GraphQL code | Example |
| :-: | :--- | :--- |
| 401 | `UNAUTHENTICATED` | no token, bad token, wrong password |
| 403 | `FORBIDDEN` | staff user calls `deleteItem` |
| 404 | `NOT_FOUND` | item or user does not exist |
| 409 | `CONFLICT` | email already registered |
| 400 / 422 | `BAD_USER_INPUT` | `quantity: -1`, `price: 0` |

---

## 8. REST vs GraphQL

| | REST (built) | GraphQL (this design) |
| :--- | :--- | :--- |
| URLs | many | one: `/graphql` |
| Response fields | server decides | client decides |
| Errors | HTTP status (401, 404 ...) | HTTP 200 + `errors` list |
| Docs | Swagger (`/docs`) | schema / GraphiQL |
| Auth, roles, database | JWT, 3 roles, PostgreSQL | **same** |