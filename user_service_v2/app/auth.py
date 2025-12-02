from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from bson import ObjectId
from app.db import users_collection

# =======================================================
# JWT SETTINGS
# =======================================================

SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_THIS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# HTTP Bearer (correct for JWT)
auth_scheme = HTTPBearer()

# Password hashing using bcrypt_sha256
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


# =======================================================
# PASSWORD HELPERS
# =======================================================

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


# =======================================================
# CREATE JWT TOKEN
# =======================================================

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =======================================================
# GET CURRENT USER (JWT REQUIRED)
# =======================================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):

    token = credentials.credentials  # Extract only the JWT part

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(401, "Invalid token: user missing")

        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(404, "User does not exist")

        return user

    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
