from pydantic import BaseModel, EmailStr


# ---------------------------
#  MODEL FOR USER CREATION
# ---------------------------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    delivery_address: str


# ---------------------------
#  MODEL FOR UPDATING ONLY EMAIL
# ---------------------------
class UpdateEmail(BaseModel):
    email: EmailStr


# ---------------------------
#  MODEL FOR UPDATING ONLY ADDRESS
# ---------------------------
class UpdateAddress(BaseModel):
    delivery_address: str


# ---------------------------
#  MODEL RETURNED TO CLIENT
# ---------------------------
class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    delivery_address: str
