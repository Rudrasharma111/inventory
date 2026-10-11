from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.security import get_current_user, require_admin_or_manager
from app.database import get_db
from app.models import Item, User
from app.schemas import Id, ItemIn, ItemOut, ItemPage, MessageOut

router = APIRouter(prefix="/items", tags=["Items"])
def get_item_or_404(item_id: int, db: Session) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item

@router.post("", response_model=ItemOut, status_code=201)
def create_item(data: ItemIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = Item(**data.model_dump(), created_by=user.id)  # created_by comes from the token, not the body
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("", response_model=ItemPage)
def list_items(
    page: int = Query(1, ge=1, le=100000),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Filter by item name"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Item)
    if search:  # case-insensitive "contains"; autoescape treats % and _ as normal letters
        query = query.filter(func.lower(Item.name).contains(search.lower(), autoescape=True))
    total = query.count()  # lets the client build page numbers
    # pagination: skip the earlier pages, then take one page (ordered by id so pages stay stable)
    items = query.order_by(Item.id).offset((page - 1) * limit).limit(limit).all()
    return ItemPage(page=page, limit=limit, total=total, items=items)

@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: Id, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_item_or_404(item_id, db)

@router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: Id, data: ItemIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_item_or_404(item_id, db)  # any logged-in user may update any item
    item.name, item.quantity, item.price = data.name, data.quantity, data.price
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}", response_model=MessageOut)
def delete_item(item_id: Id, db: Session = Depends(get_db), user: User = Depends(require_admin_or_manager)):
    db.delete(get_item_or_404(item_id, db))
    db.commit()
    return MessageOut(message="Item deleted successfully")