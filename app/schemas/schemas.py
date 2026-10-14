from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str

class RoleUpdate(BaseModel):
    role: Literal["inventory_manager", "staff"]

class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0)
    price: float = Field(ge=0.01, le=99999999.99)

class ItemOut(ItemIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: int

class ItemPage(BaseModel):
    page: int
    limit: int
    total: int
    items: list[ItemOut]