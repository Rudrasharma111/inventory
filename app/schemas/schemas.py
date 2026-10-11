from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

class SignupRequest(BaseModel):
    name: Name
    email: EmailStr  
    phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > 72:  
            raise ValueError("Password is too long")
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str


class RoleUpdate(BaseModel):
    role: Literal["inventory_manager", "staff"]


class ItemIn(BaseModel):
    name: Name
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