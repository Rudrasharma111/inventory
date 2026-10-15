from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.models import User
from app.schemas.schemas import RoleUpdate, UserOut
from app.core.security import require_admin

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(require_admin)])

@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()

@router.patch("/{user_id}/role", response_model=UserOut)
def change_role(user_id: int, data: RoleUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "admin":
        raise HTTPException(400, "The admin's role cannot be changed")
    user.role = data.role
    db.commit()
    db.refresh(user)
    return user