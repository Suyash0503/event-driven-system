from pydantic import BaseModel
from typing import Optional

# --------------------------------------
# Order creation input (client sends this)
# --------------------------------------
class OrderCreate(BaseModel):
    user_id: str
    email: str
    delivery_address: str
    item: str
    quantity: int


# --------------------------------------
# Order update (client changes order info)
# NOTE: only "status" should be updated normally
# --------------------------------------
class OrderUpdate(BaseModel):
    item: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None   # "under process", "shipping", "delivered"


# --------------------------------------
# Response model (returned to client)
# --------------------------------------
class OrderResponse(BaseModel):
    id: str
    user_id: str
    email: str
    delivery_address: str
    item: str
    quantity: int
    status: str
