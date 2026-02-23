from fastapi import FastAPI, HTTPException
from bson import ObjectId

from app.db import orders_collection
from app.models import OrderCreate, OrderUpdate, OrderResponse

app = FastAPI(title="Order Service")


# ---------------------------------
# Helper: convert DB doc to response
# ---------------------------------
def to_response(order_doc):
    return OrderResponse(
        id=str(order_doc["_id"]),
        user_id=order_doc["user_id"],
        email=order_doc["email"],
        delivery_address=order_doc["delivery_address"],
        item=order_doc["item"],
        quantity=order_doc["quantity"],
        status=order_doc["status"]
    )


# ---------------------------------
# Create a new order
# ---------------------------------
@app.post("/orders", response_model=OrderResponse)
def create_order(data: OrderCreate):

    new_order = {
        "user_id": data.user_id,
        "email": data.email,
        "delivery_address": data.delivery_address,
        "item": data.item,
        "quantity": data.quantity,
        "status": "under process"   # assignment says: under process, shipping, delivered
    }

    result = orders_collection.insert_one(new_order)
    order = orders_collection.find_one({"_id": result.inserted_id})

    return to_response(order)


# ---------------------------------
# Get order by ID
# ---------------------------------
@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    try:
        oid = ObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = orders_collection.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return to_response(order)


# ---------------------------------
# Update order (usually status only)
# ---------------------------------
@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: str, data: OrderUpdate):
    try:
        oid = ObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    updated = orders_collection.find_one_and_update(
        {"_id": oid},
        {"$set": update_data},
        return_document=True
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    return to_response(updated)
