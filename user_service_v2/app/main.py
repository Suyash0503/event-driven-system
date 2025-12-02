from fastapi import FastAPI, HTTPException, Depends
from bson import ObjectId

from app.db import users_collection
from app.models import UserBase, UserUpdate, UserResponse, Login, Token
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

app = FastAPI(title="User Service v2 with JWT Auth")


# -------------------------
# Convert MongoDB doc -> Pydantic response
# -------------------------
def to_user_response(doc):
    return UserResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        delivery_address=doc["delivery_address"],
    )


# -------------------------
# REGISTER USER
# -------------------------
@app.post("/users", response_model=UserResponse)
def create_user(user: UserBase):
    # Hash password before saving
    new_user = user.dict()
    new_user["password"] = hash_password(user.password)

    result = users_collection.insert_one(new_user)
    created = users_collection.find_one({"_id": result.inserted_id})

    return to_user_response(created)


# -------------------------
# LOGIN (Generate JWT Token)
# -------------------------
@app.post("/login", response_model=Token)
def login(credentials: Login):
    user = users_collection.find_one({"email": credentials.email})

    if not user:
        raise HTTPException(401, "Invalid email or password")

    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(401, "Invalid email or password")

    # Create token with user id as the subject
    token = create_access_token({"sub": str(user["_id"])})

    return Token(access_token=token)


# -------------------------
# GET USER BY ID (Protected)
# -------------------------
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(400, "Invalid user ID")

    user = users_collection.find_one({"_id": oid})

    if not user:
        raise HTTPException(404, "User not found")

    return to_user_response(user)


# -------------------------
# UPDATE USER (Protected)
# -------------------------
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    updates: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
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


# -------------------------
# GET PROFILE (Protected)
# -------------------------
@app.get("/profile", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return to_user_response(current_user)
