from sqlalchemy import Column, ForeignKey, Integer, Numeric, String

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=True)  # NULL for Google-only users
    role = Column(String(20), nullable=False, default="staff")  # admin / inventory_manager / staff


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False)  # exact decimal, good for money
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
