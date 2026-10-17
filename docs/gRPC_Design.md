# gRPC Design

Project: **Inventory Service** (FastAPI + PostgreSQL + JWT)
File: `inventory.proto` (proto3) | Server port: `50051`

This is a **design file**. The running API is REST. gRPC here describes the **same app**: same JWT, same roles, same validation rules, same tables (`users`, `items`).

---

## 1. What is gRPC?

- Calls a function on another server like a normal function call (RPC = Remote Procedure Call).
- The calls and data are written once in a **`.proto` file**. Code for Python (or any language) is generated from it.
- Data is sent as **binary** (Protocol Buffers) over **HTTP/2**. It is smaller and faster than JSON.
- Best for **service-to-service** calls inside the backend. Browsers cannot call gRPC directly.

---

## 2. How a call flows

```
Client / other service
   |  CreateItem(name, quantity, price)   + metadata: authorization: Bearer <JWT>
   v
gRPC server (port 50051)
   -> interceptor: check token, load user, check role
   -> servicer method CreateItem()
   -> SQLAlchemy -> PostgreSQL
   v
Response message: Item { id, name, quantity, price, created_by }
```

---

## 3. inventory.proto

```proto
syntax = "proto3";
package inventory.v1;

enum Role {
  ROLE_UNSPECIFIED = 0;
  ROLE_ADMIN = 1;
  ROLE_INVENTORY_MANAGER = 2;
  ROLE_STAFF = 3;
}

// ---------- Data ----------
message User {
  int32 id = 1;
  string name = 2;
  string email = 3;
  Role role = 4;
}

message Item {
  int32 id = 1;
  string name = 2;
  int32 quantity = 3;
  double price = 4;
  int32 created_by = 5;
}

// ---------- Auth ----------
message SignupRequest       { string name = 1;  string email = 2;  string password = 3; }
message LoginRequest        { string email = 1; string password = 2; }
message GoogleLoginRequest  { string id_token = 1; }
message TokenResponse       { string access_token = 1; string token_type = 2; Role role = 3; }

// ---------- Items ----------
message CreateItemRequest   { string name = 1; int32 quantity = 2; double price = 3; }
message GetItemRequest      { int32 id = 1; }
message UpdateItemRequest   { int32 id = 1; string name = 2; int32 quantity = 3; double price = 4; }
message DeleteItemRequest   { int32 id = 1; }
message DeleteItemResponse  { bool deleted = 1; }

message ListItemsRequest {
  int32 page = 1;                // 0 = use default (1)
  int32 limit = 2;               // 0 = use default (10), max 100
  optional int32 created_by = 3; // only items of this user
}
message ListItemsResponse {
  int32 page = 1;
  int32 limit = 2;
  int32 total = 3;
  repeated Item items = 4;
}

// ---------- Users ----------
message ListUsersRequest {}
message ListUsersResponse { repeated User users = 1; }
message ChangeUserRoleRequest { int32 user_id = 1; Role role = 2; }

// ---------- Health ----------
message HealthRequest {}
message HealthResponse { string status = 1; }

// ---------- Service ----------
service InventoryService {
  rpc Health(HealthRequest) returns (HealthResponse);

  rpc Signup(SignupRequest) returns (User);
  rpc Login(LoginRequest) returns (TokenResponse);
  rpc GoogleLogin(GoogleLoginRequest) returns (TokenResponse);

  rpc CreateItem(CreateItemRequest) returns (Item);
  rpc GetItem(GetItemRequest) returns (Item);
  rpc ListItems(ListItemsRequest) returns (ListItemsResponse);
  rpc UpdateItem(UpdateItemRequest) returns (Item);
  rpc DeleteItem(DeleteItemRequest) returns (DeleteItemResponse);

  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
  rpc ChangeUserRole(ChangeUserRoleRequest) returns (User);
}
```

Rules (same as REST):
- `name`: 1-100 characters. `quantity`: 0 or more. `price`: more than 0. `password`: 8-64 characters.
- `ChangeUserRole` can set only `ROLE_STAFF` or `ROLE_INVENTORY_MANAGER`. The role of an admin cannot be changed.
- Signup and Google login always create a `ROLE_STAFF` user.

---

## 4. Methods, access and REST equivalent

| RPC method | Who can call | REST equivalent |
| :--- | :--- | :--- |
| `Health` | public | `GET /health` |
| `Signup` | public | `POST /auth/signup` |
| `Login` | public | `POST /auth/login` |
| `GoogleLogin` | public | `POST /auth/google` |
| `CreateItem` | any logged-in user | `POST /items` |
| `ListItems` | any logged-in user | `GET /items?page=&limit=` |
| `GetItem` | any logged-in user | `GET /items/{id}` |
| `UpdateItem` | any logged-in user | `PUT /items/{id}` |
| `DeleteItem` | inventory_manager, admin | `DELETE /items/{id}` |
| `ListUsers` | admin | `GET /users` |
| `ChangeUserRole` | admin | `PATCH /users/{id}/role` |

---

## 5. Auth

Same JWT as REST (see `JWT_Design.md`). The token goes in the call **metadata** (like an HTTP header):

```
authorization: Bearer <access_token>
```

A server **interceptor** runs before every method. It checks the token, loads the user from the database (the role comes from the database) and checks the role for that method.

---

## 6. Errors (REST to gRPC)

| REST | gRPC status | Example |
| :-: | :--- | :--- |
| 401 | `UNAUTHENTICATED` | no token, bad token, wrong password |
| 403 | `PERMISSION_DENIED` | staff user calls `DeleteItem` |
| 404 | `NOT_FOUND` | item or user does not exist |
| 409 | `ALREADY_EXISTS` | email already registered |
| 400 / 422 | `INVALID_ARGUMENT` | `quantity` is negative, `price` is 0 |
| 503 | `UNAVAILABLE` | Google login is not configured |
| 500 | `INTERNAL` | unexpected error |

---

## 7. Example call (grpcurl)

```bash
# login
grpcurl -plaintext -d '{"email":"user@example.com","password":"password123"}' \
  localhost:50051 inventory.v1.InventoryService/Login

# create an item (with token)
grpcurl -plaintext -H "authorization: Bearer <token>" \
  -d '{"name":"Keyboard","quantity":10,"price":49.99}' \
  localhost:50051 inventory.v1.InventoryService/CreateItem
```
Response:
```json
{ "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "createdBy": 2 }
```

---

## 8. REST vs gRPC

| | REST (built) | gRPC (this design) |
| :--- | :--- | :--- |
| Data format | JSON (text) | Protobuf (binary) |
| Transport | HTTP/1.1 | HTTP/2 |
| Contract | OpenAPI / Swagger | `.proto` file |
| Used by | browsers, apps | other backend services |
| Errors | HTTP status | gRPC status codes |
| Auth, roles, database | JWT, 3 roles, PostgreSQL | **same** |