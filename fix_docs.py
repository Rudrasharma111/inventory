import re
import os

def edit(path, plain=(), regex=()):
    # Check if file exists (kyunki docs folder mein ho ya root mein, dono check karega)
    if not os.path.exists(path):
        # Fallback to root folder if not in docs/
        alt_path = os.path.basename(path)
        if os.path.exists(alt_path):
            path = alt_path
        else:
            print(f"SKIPPED {path} | File not found")
            return

    with open(path, encoding="utf-8", newline="") as f:
        s = f.read()
        
    for old, new in plain:
        if old in s:
            s = s.replace(old, new)
            print("OK     ", path, "|", old[:50])
        else:
            print("MISSING", path, "|", old[:50])
            
    for pat, new in regex:
        s, n = re.subn(pat, new, s, flags=re.M)
        print("OK     " if n else "MISSING", path, "|", pat[:50])
        
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(s)

edit("README.md",
     plain=[("staff (own items only), manager, admin | 200 | 401, 403, 404, 422",
             "any logged-in user (staff, manager, admin) | 200 | 401, 404, 422"),
            ("| Update own items |", "| Update items |")],
     regex=[(r"^\| Update any item \|.*\r?\n", ""),
            (r"^14\. \[Known limitations\].*\r?\n", ""),
            (r"^15\. \[Troubleshooting\].*\r?\n", "")])

edit("docs/REST_API_Design.md",
     plain=[("logged in (staff: own items only) | 200 | 401, 403, 404, 422", "logged in | 200 | 401, 404, 422")])

edit("docs/GraphQL_Design.md",
     plain=[("# staff: own items only", "# any logged-in user")],
     regex=[(r"^The business rules \(staff can update only own items.*$",
             "The business rules (any logged-in user can update items, only admin/manager can delete, the role comes from the database, 409 on a duplicate email) are the same in REST, GraphQL and gRPC.")])

edit("docs/gRPC_Design.md",
     plain=[("// staff: own items only", "// any logged-in user")])

edit("docs/JWT_Design.md",
     plain=[("Create and read items, update **own** items", "Create, read and update items"),
            ("Everything staff can do + update any item + delete items", "Everything staff can do + delete items")])