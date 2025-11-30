from pydantic import BaseModel, EmailStr
from typing import Optional


# Base Model for creating a user
class UserBase(BaseModel):
    name: str
    email: EmailStr
    delivery_address: str


# Cleaner update model (one model instead of two in v1)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None


# Response model
class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    delivery_address: str
