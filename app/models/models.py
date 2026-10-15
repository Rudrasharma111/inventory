from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from app.database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True) 
    role = Column(String(20), nullable=False, default="staff")  

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False) 
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)