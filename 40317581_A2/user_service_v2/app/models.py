from pydantic import BaseModel, EmailStr
from typing import Optional


# Base Model for creating a user
class UserBase(BaseModel):
    name: str
    email: EmailStr
    delivery_address: str
    password: str   # Password added (required for login)


# Cleaner update model
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None


# Response model
class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    delivery_address: str


# Login request model
class Login(BaseModel):
    email: str
    password: str


# Token response model
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
