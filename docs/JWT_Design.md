# JWT Design

- Library: PyJWT · Algorithm: HS256 · Secret: `SECRET_KEY` from `.env` · Lifetime: 60 minutes
- Sent as: `Authorization: Bearer <token>`

## Claims
| Claim | Example | Meaning |
| :--- | :--- | :--- |
| `sub` | `"1"` | User id (this is what the server uses) |
| `email` | `"user@example.com"` | User's email |
| `role` | `"staff"` | `admin`, `inventory_manager` or `staff` (for the client to show; see below) |
| `iat` | `1760000000` | Issued at |
| `exp` | `1760003600` | Expires at (`iat` + 60 min) |

```json
{ "sub": "1", "email": "user@example.com", "role": "staff", "iat": 1760000000, "exp": 1760003600 }
```

## Flow
1. `POST /auth/login` (or `/auth/google`) returns the token.
2. The client sends the token with every request.
3. The server checks the signature and expiry, then **loads the user from the database** using `sub`.
4. Missing, invalid or expired token, or a user that no longer exists → `401`.
5. A route that needs `admin` but the user's role is `staff` → `403`.

## The role comes from the database, not from the token
The token is signed, so nobody can edit it. But a token stays valid until it expires, so a role written inside it can get old (for example, a manager who was made `staff` would still look like a manager for up to 60 minutes). That is why the server always uses the role stored in the database: role changes and deleted users apply immediately, and nobody needs to log in again. The `role` claim is only a convenience for the client.

## Roles
| Role | How you get it | Can do |
| :--- | :--- | :--- |
| `staff` | Default for every signup / Google login | Create and read items, update **own** items |
| `inventory_manager` | An admin promotes a user with `PATCH /users/{id}/role` | Everything staff can do + update any item + delete items |
| `admin` | Created from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` on every startup (nobody else can become admin) | Everything a manager can do + list users + manage roles |

## Security notes
- There is no refresh token and no logout list: a token simply expires after 60 minutes. Deleting or demoting a user is still immediate (see above).
- `SECRET_KEY` has no default value: the app does not start without it. Keep `.env` out of git.
- Passwords are stored as bcrypt hashes. Google users have no password.
