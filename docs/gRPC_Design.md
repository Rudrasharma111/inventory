# gRPC Design

Project: **Inventory Service**. This is a **design only** file (the running API is REST). It shows how the same app would look as a gRPC service, with the same rules, the same JWT and the same database.

---

## 1. What is gRPC? (short)

gRPC is a way to call a function on another server as if it were local (RPC = Remote Procedure Call).

- Contract is written in a **`.proto` file** (Protocol Buffers).
- Data is sent in a small **binary** format (not text JSON).
- It runs on **HTTP/2** (fast, many calls on one connection, streaming).
- Code for client and server is **generated** from the `.proto` file.
- Best for **service-to-service** calls inside a backend.

---

## 2. Architecture flow (block diagram)

### 2.1 Big picture

```
 +-------------------+     HTTP/2 + Protobuf (binary)    +---------------------------+
 |  gRPC client      |  rpc InventoryService/CreateItem  |  gRPC server (port 50051) |
 |  (another service |  metadata: authorization: Bearer  |                           |
 |   / grpcurl)      | --------------------------------> |  Python grpcio            |
 |                   | <-------------------------------- |                           |
 +-------------------+     response message + status     +-------------+-------------+
        ^                                                              |
        | generated stub (from inventory.proto)                        v
                                                         +---------------------------+
                                                         |  PostgreSQL 15            |
                                                         +---------------------------+
```

### 2.2 One request inside the code (example: `CreateItem`)

```
 Client (stub)
   |  stub.CreateItem(CreateItemRequest(name="Keyboard", quantity=10, price=49.99),
   |                  metadata=[("authorization","Bearer <JWT>")])
   v
+----------------------------------------------------------------------+
| 1. Serialize to Protobuf bytes, send over HTTP/2                     |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 2. Server Interceptor (auth)                                         |
|    read metadata "authorization", check JWT, load user from DB       |
|    check role for this method (UNAUTHENTICATED / PERMISSION_DENIED)  |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 3. Servicer  InventoryService.CreateItem()                           |
|    validate fields (quantity >= 0 ...) -> INVALID_ARGUMENT           |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 4. Same service function as REST / GraphQL                           |
|    SQLAlchemy -> PostgreSQL INSERT                                   |
+------------------------------+---------------------------------------+
                               v
+----------------------------------------------------------------------+
| 5. Build Item message, send back as Protobuf + status OK             |
+----------------------------------------------------------------------+
```

---

## 3. inventory.proto

```proto
syntax = "proto3";
package inventory.v1;

import "google/protobuf/empty.proto";

enum Role {
  ROLE_UNSPECIFIED = 0;
  ROLE_ADMIN = 1;
  ROLE_INVENTORY_MANAGER = 2;
  ROLE_STAFF = 3;
}

message User {
  int32 id = 1;
  string name = 2;
  string email = 3;
  optional string phone = 4;
  Role role = 5;
}

message Item {
  int32 id = 1;
  string name = 2;
  int32 quantity = 3;          // >= 0
  double price = 4;            // 0.01 .. 99999999.99
  int32 created_by = 5;        // users.id
}

// ---- Auth ----
message SignupRequest {
  string name = 1;
  string email = 2;
  optional string phone = 3;
  string password = 4;
}
message LoginRequest       { string email = 1; string password = 2; }
message GoogleLoginRequest { string id_token = 1; }
message TokenResponse      { string access_token = 1; string token_type = 2; Role role = 3; }

// ---- Items ----
message CreateItemRequest { string name = 1; int32 quantity = 2; double price = 3; }
message GetItemRequest    { int32 id = 1; }
message UpdateItemRequest { int32 id = 1; string name = 2; int32 quantity = 3; double price = 4; }
message DeleteItemRequest { int32 id = 1; }
message ListItemsRequest  { int32 page = 1; int32 limit = 2; optional string search = 3; }
message ListItemsResponse { int32 page = 1; int32 limit = 2; int32 total = 3; repeated Item items = 4; }

// ---- Users (admin only) ----
enum AssignableRole {
  ASSIGNABLE_ROLE_UNSPECIFIED = 0;
  ASSIGNABLE_ROLE_INVENTORY_MANAGER = 1;
  ASSIGNABLE_ROLE_STAFF = 2;
}
message ListUsersResponse     { repeated User users = 1; }
message UpdateUserRoleRequest { int32 id = 1; AssignableRole role = 2; }

message HealthResponse { string status = 1; }

// ---- Services ----
service HealthService {
  rpc Check (google.protobuf.Empty) returns (HealthResponse);
}

service AuthService {                       // all public
  rpc Signup (SignupRequest) returns (User);
  rpc Login (LoginRequest) returns (TokenResponse);
  rpc GoogleLogin (GoogleLoginRequest) returns (TokenResponse);
}

service InventoryService {                  // logged in
  rpc CreateItem (CreateItemRequest) returns (Item);
  rpc GetItem (GetItemRequest) returns (Item);
  rpc ListItems (ListItemsRequest) returns (ListItemsResponse);
  rpc UpdateItem (UpdateItemRequest) returns (Item);
  rpc DeleteItem (DeleteItemRequest) returns (google.protobuf.Empty);   // manager / admin
}

service UserService {                       // admin only
  rpc ListUsers (google.protobuf.Empty) returns (ListUsersResponse);
  rpc UpdateUserRole (UpdateUserRoleRequest) returns (User);
}
```

Notes: field numbers (`= 1`, `= 2` ...) must never change after release. `page = 0` / `limit = 0` mean "not set" (defaults 1 and 10, max 100).

---

## 4. Auth and roles

- Same JWT as REST, sent in **call metadata**: `authorization: Bearer <access_token>`.
- Public calls: `Health.Check`, `Auth.Signup`, `Auth.Login`, `Auth.GoogleLogin`.
- A **server interceptor** checks the token and loads the user from the database (role comes from the DB, not the token).

| Call | staff | inventory_manager | admin |
| :--- | :-: | :-: | :-: |
| CreateItem, GetItem, ListItems, UpdateItem | yes | yes | yes |
| DeleteItem | no | yes | yes |
| ListUsers, UpdateUserRole | no | no | yes |

---

## 5. Error mapping (REST to gRPC)

| REST | gRPC status | When |
| :-: | :--- | :--- |
| 400 | `FAILED_PRECONDITION` | Changing the admin's role |
| 401 | `UNAUTHENTICATED` | No / bad / expired token, wrong login |
| 403 | `PERMISSION_DENIED` | Role not allowed |
| 404 | `NOT_FOUND` | Item or user not found |
| 409 | `ALREADY_EXISTS` | Email already registered |
| 422 | `INVALID_ARGUMENT` | Invalid field values |
| 503 | `UNAVAILABLE` | Google login not configured |

---

## 6. REST to gRPC map

| REST | gRPC |
| :--- | :--- |
| `GET /health` | `HealthService.Check` |
| `POST /auth/signup` | `AuthService.Signup` |
| `POST /auth/login` | `AuthService.Login` |
| `POST /auth/google` | `AuthService.GoogleLogin` |
| `POST /items` | `InventoryService.CreateItem` |
| `GET /items?page&limit&search` | `InventoryService.ListItems` |
| `GET /items/{id}` | `InventoryService.GetItem` |
| `PUT /items/{id}` | `InventoryService.UpdateItem` |
| `DELETE /items/{id}` | `InventoryService.DeleteItem` |
| `GET /users` | `UserService.ListUsers` |
| `PATCH /users/{id}/role` | `UserService.UpdateUserRole` |

---

## 7. Example: how to build ONE endpoint in gRPC (`CreateItem`)

**Step 1 - Write the contract** (`inventory.proto`): `CreateItemRequest`, `Item`, and `rpc CreateItem` (see section 3).

**Step 2 - Generate code:**
```bash
pip install grpcio grpcio-tools
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. inventory.proto
```
This creates `inventory_pb2.py` (messages) and `inventory_pb2_grpc.py` (service base classes).

**Step 3 - Implement the servicer:**
```python
class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    def CreateItem(self, request, context):
        user = context.user                               # set by the auth interceptor
        if request.quantity < 0 or not (0.01 <= request.price <= 99999999.99):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid quantity or price")
        with SessionLocal() as db:
            item = Item(name=request.name, quantity=request.quantity,
                        price=request.price, created_by=user.id)
            db.add(item); db.commit(); db.refresh(item)
            return inventory_pb2.Item(id=item.id, name=item.name, quantity=item.quantity,
                                      price=float(item.price), created_by=item.created_by)
```

**Step 3b - Auth interceptor:**
```python
class AuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, details):
        meta = dict(details.invocation_metadata)
        token = meta.get("authorization", "").removeprefix("Bearer ")
        # check JWT + load user, otherwise abort with UNAUTHENTICATED
        return continuation(details)
```

**Step 4 - Start the server:**
```python
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=[AuthInterceptor()])
inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryService(), server)
server.add_insecure_port("[::]:50051")
server.start(); server.wait_for_termination()
```

**Step 5 - Call it** (`grpcurl` or Python client):
```bash
grpcurl -plaintext -H "authorization: Bearer <token>" \
  -d '{"name":"Keyboard","quantity":10,"price":49.99}' \
  localhost:50051 inventory.v1.InventoryService/CreateItem
```
```json
{ "id": 1, "name": "Keyboard", "quantity": 10, "price": 49.99, "createdBy": 2 }
```
(`docker-compose.yml` would also expose port `50051`.)

---

## 8. Why gRPC (and when)
- Very fast and small messages (binary).
- Strong contract and generated clients in many languages.
- Streaming is built in.
- Cost: browsers cannot call it directly (needs gRPC-Web), and binary data is hard to read by eye.