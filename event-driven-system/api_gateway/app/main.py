from fastapi import FastAPI, HTTPException
import httpx
import json
import os
import random

# -------------------------------------------------
# Load gateway_config.json from the ROOT directory
# -------------------------------------------------
CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "gateway_config.json")
)

print(f" Loading configuration from: {CONFIG_PATH}")

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"gateway_config.json not found at {CONFIG_PATH}")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# Load services and split ratio
services = config["services"]
split_ratio = config["routing"]["user_split"]   # e.g., 0.7 (70% to v1)

app = FastAPI(title="API Gateway")


# -------------------------------------------------
# Forward request to microservices
# -------------------------------------------------
async def forward_request(method: str, url: str, data=None):
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                r = await client.get(url)
            elif method == "POST":
                r = await client.post(url, json=data)
            elif method == "PUT":
                r = await client.put(url, json=data)
            else:
                raise HTTPException(status_code=400, detail="Invalid HTTP Method")

            return r.json()

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# STRANGLER PATTERN — 70% V1, 30% V2 BASED ON CONFIG
# -------------------------------------------------
def choose_user_service():
    """
    Uses the split_ratio from gateway_config.json:
    Example:
    - user_split = 0.7 → 70% traffic to v1, 30% to v2
    """

    rand_val = random.random()
    print(f" Random = {rand_val} | user_split = {split_ratio}")

    if rand_val < split_ratio:
        print("➡ Routing to USER SERVICE V1 (v1)")
        return services["user_v1"]

    print("➡ Routing to USER SERVICE V2 (v2)")
    return services["user_v2"]


# -------------------------------------------------
# USER ROUTES (apply strangler pattern)
# -------------------------------------------------
@app.post("/users")
async def strangler_create_user(data: dict):
    base = choose_user_service()
    return await forward_request("POST", f"{base}/users", data)


@app.get("/users/{user_id}")
async def strangler_get_user(user_id: str):
    base = choose_user_service()
    return await forward_request("GET", f"{base}/users/{user_id}")


@app.put("/users/{user_id}/email")
async def strangler_update_email(user_id: str, data: dict):
    base = choose_user_service()
    return await forward_request("PUT", f"{base}/users/{user_id}/email", data)


@app.put("/users/{user_id}/address")
async def strangler_update_address(user_id: str, data: dict):
    base = choose_user_service()
    return await forward_request("PUT", f"{base}/users/{user_id}/address", data)


# -------------------------------------------------
# ORDER ROUTES (NO strangler pattern)
# -------------------------------------------------
@app.post("/orders")
async def create_order(data: dict):
    return await forward_request("POST", f"{services['order_service']}/orders", data)


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    return await forward_request("GET", f"{services['order_service']}/orders/{order_id}")
