from fastapi import FastAPI, HTTPException
from bson import ObjectId
from app.db import users_collection
from app.models import UserBase, UserUpdate, UserResponse

app = FastAPI(title="User Service v2 (Refactored)")


# Convert MongoDB doc -> pydantic response
def to_user_response(doc):
    return UserResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        delivery_address=doc["delivery_address"]
    )


# Create user
@app.post("/users", response_model=UserResponse)
def create_user(user: UserBase):
    new_user = user.dict()
    result = users_collection.insert_one(new_user)
    created = users_collection.find_one({"_id": result.inserted_id})
    return to_user_response(created)


# Get user by ID
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(400, "Invalid user ID")

    user = users_collection.find_one({"_id": oid})

    if not user:
        raise HTTPException(404, "User not found")

    return to_user_response(user)


# Update (email and/or address)
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, updates: UserUpdate):
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(400, "Invalid user ID")

    update_data = {k: v for k, v in updates.dict().items() if v is not None}

    updated = users_collection.find_one_and_update(
        {"_id": oid},
        {"$set": update_data},
        return_document=True
    )

    if not updated:
        raise HTTPException(404, "User not found")

    return to_user_response(updated)
