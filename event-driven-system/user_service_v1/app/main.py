from fastapi import FastAPI, HTTPException
from bson import ObjectId

from app.models import UserCreate, UpdateEmail, UpdateAddress, UserResponse
from app.db import users_collection
from app.publisher import publish_event

app = FastAPI(title="User Service v1")


# ---------------------------------------------
# Helper: Convert MongoDB document → Pydantic
# ---------------------------------------------
def user_to_response(user_doc):
    return UserResponse(
        id=str(user_doc["_id"]),
        name=user_doc["name"],
        email=user_doc["email"],
        delivery_address=user_doc["delivery_address"]
    )


# ---------------------------------------------
# CREATE USER (No event published here)
# ---------------------------------------------
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    new_user = {
        "name": user.name,
        "email": user.email,
        "delivery_address": user.delivery_address
    }

    result = users_collection.insert_one(new_user)
    created_user = users_collection.find_one({"_id": result.inserted_id})

    return user_to_response(created_user)


# ---------------------------------------------
# GET USER BY ID
# ---------------------------------------------
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = users_collection.find_one({"_id": obj_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_to_response(user)


# ---------------------------------------------
# UPDATE EMAIL + PUBLISH EVENT
# ---------------------------------------------
@app.put("/users/{user_id}/email", response_model=UserResponse)
def update_email(user_id: str, data: UpdateEmail):
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    updated = users_collection.find_one_and_update(
        {"_id": obj_id},
        {"$set": {"email": data.email}},
        return_document=True
    )

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    # ---- Publish Email Updated Event ----
    event = {
        "type": "email_updated",
        "user_id": user_id,
        "new_email": data.email
    }
    publish_event(event)

    return user_to_response(updated)


# ---------------------------------------------
# UPDATE ADDRESS + PUBLISH EVENT
# ---------------------------------------------
@app.put("/users/{user_id}/address", response_model=UserResponse)
def update_address(user_id: str, data: UpdateAddress):
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    updated = users_collection.find_one_and_update(
        {"_id": obj_id},
        {"$set": {"delivery_address": data.delivery_address}},
        return_document=True
    )

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    # ---- Publish Address Updated Event ----
    event = {
        "type": "address_updated",
        "user_id": user_id,
        "new_address": data.delivery_address
    }
    publish_event(event)

    return user_to_response(updated)
