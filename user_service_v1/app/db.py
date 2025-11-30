from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Atlas URL
MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(
    MONGO_URL,
    tls=True,
    tlsAllowInvalidCertificates=True
)

# V1 → writes to user_db.users
db = client["user_db"]
users_collection = db["users"]
