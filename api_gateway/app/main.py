from fastapi import FastAPI, HTTPException
import httpx
import json
import os
import random
import uuid
from typing import Any, Dict, List, Literal, Optional
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "gateway_config.json")
)

print(f"Loading configuration from: {CONFIG_PATH}")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

services = config["services"]
split_ratio = float(config["routing"]["user_split"])

# Agent mode switch
AGENT_MODE = os.getenv("AGENT_MODE", "false").lower() == "true"

# Orchestrator URL (local default)
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:8004")

print("AGENT_MODE =", AGENT_MODE)
print("ORCHESTRATOR_URL =", ORCHESTRATOR_URL)

# Minimal reliability switch: force v1 (recommended while debugging)
FORCE_USER_V1 = os.getenv("FORCE_USER_V1", "true").lower() == "true"

# OpenAI config (set OPENAI_API_KEY in your environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if you want
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

app = FastAPI(title="API Gateway")


async def forward_request(method: str, url: str, data=None):
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                r = await client.get(url)
            elif method == "POST":
                r = await client.post(url, json=data)
            elif method == "PUT":
                r = await client.put(url, json=data)
            else:
                raise HTTPException(status_code=400, detail="Invalid HTTP Method")

            r.raise_for_status()
            content_type = r.headers.get("content-type", "")
            if "application/json" in content_type:
                return r.json()
            return {"raw": r.text}

        except httpx.HTTPStatusError as e:
            detail = e.response.text or repr(e)
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except Exception as e:
            print("[Gateway] error:", repr(e))
            raise HTTPException(status_code=500, detail=repr(e))


def choose_user_service() -> str:
    if FORCE_USER_V1:
        return services["user_v1"]

    rand_val = random.random()
    return services["user_v1"] if rand_val < split_ratio else services["user_v2"]


# -----------------------------
# NLP -> PLAN (OpenAI)
# -----------------------------
SYSTEM_PROMPT = """
You are a command parser for an e-commerce backend.

Convert the user's message into STRICT JSON only.

Output schema:
{
  "actions": [
    { "type": "create_user", "name": "...", "email": "...", "address": "..." },
    { "type": "update_address", "user_id": "...", "address": "..." } OR { "type": "update_address", "user_email": "...", "address": "..." },
    { "type": "create_order", "user_id": "...", "product_id": "p1", "quantity": 2 } OR { "type": "create_order", "user_email": "...", "product_id": "p1", "quantity": 2 },
    { "type": "checkout", "order_id": "..." } OR { "type": "checkout", "order_ref": "last_order" },
    { "type": "list_products" }
  ]
}

Rules:
- Return ONLY valid JSON. No markdown, no backticks, no explanations.
- Use only these action types: create_user, update_address, list_products, create_order, checkout.
- Do NOT invent ids/emails. If missing, omit that action or keep it to list_products only.
- quantity must be an integer >= 1.
""".strip()


def _light_validate_plan(plan: Dict[str, Any]) -> None:
    if not isinstance(plan, dict) or "actions" not in plan:
        raise ValueError("Plan must be an object with 'actions'.")

    actions = plan["actions"]
    if not isinstance(actions, list) or len(actions) == 0:
        raise ValueError("'actions' must be a non-empty list.")

    allowed = {"create_user", "update_address", "list_products", "create_order", "checkout"}
    for a in actions:
        if not isinstance(a, dict) or "type" not in a:
            raise ValueError("Each action must be an object with 'type'.")
        if a["type"] not in allowed:
            raise ValueError(f"Unsupported action type: {a['type']}")
        if "quantity" in a:
            q = a["quantity"]
            if not isinstance(q, int) or q < 1:
                raise ValueError("quantity must be int >= 1")


async def openai_text_to_plan(text: str) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in environment."
        )

    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"OpenAI error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"OpenAI call failed: {repr(e)}")

    try:
        plan = json.loads(content)
        _light_validate_plan(plan)
        return plan
    except Exception as e:
        # Return model output in error so you can debug prompt issues quickly
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse model output as valid plan JSON: {repr(e)} | raw={content}"
        )


# -----------------------------
# USER ROUTES
# -----------------------------
@app.post("/users")
async def create_user(data: dict):
    base = choose_user_service()
    print(f"[Gateway] forwarding POST /users -> {base}/users")
    print(f"[Gateway] payload keys: {list(data.keys())}")

    clean = dict(data)
    clean.pop("phone", None)

    return await forward_request("POST", f"{base}/users", clean)


@app.get("/users/{user_id}")
async def get_user(user_id: str):
    if AGENT_MODE:
        return await forward_request("GET", f"{services['user_v2']}/users/{user_id}")

    base = choose_user_service()
    return await forward_request("GET", f"{base}/users/{user_id}")


@app.put("/users/{user_id}/address")
async def update_address(user_id: str, data: dict):
    if AGENT_MODE:
        return await forward_request("PUT", f"{ORCHESTRATOR_URL}/users/{user_id}/address", data)

    base = choose_user_service()
    return await forward_request("PUT", f"{base}/users/{user_id}/address", data)


# -----------------------------
# ORDER ROUTES
# -----------------------------
@app.post("/orders")
async def create_order(data: dict):
    if AGENT_MODE:
        return await forward_request("POST", f"{ORCHESTRATOR_URL}/orders", data)

    return await forward_request("POST", f"{services['order_service']}/orders", data)


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    return await forward_request("GET", f"{services['order_service']}/orders/{order_id}")


# -----------------------------
# MODE 2: NATURAL LANGUAGE -> ORCHESTRATOR
# -----------------------------
@app.post("/command-agentic")
async def command_agentic(payload: dict):
    """
    Body:
      { "text": "Create user ... then create order ... then checkout ..." }

    Flow:
      Gateway -> OpenAI (plan JSON) -> Orchestrator /execute-plan -> results
    """
    text = (payload or {}).get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=400, detail="Missing 'text' in request body.")

    request_id = str(uuid.uuid4())

    plan = await openai_text_to_plan(text.strip())

    orch_payload = {
        "request_id": request_id,
        "actions": plan.get("actions", []),
    }

    # Orchestrator must implement POST /execute-plan
    orch_result = await forward_request(
        "POST",
        f"{ORCHESTRATOR_URL}/execute-plan",
        orch_payload
    )

    return {
        "request_id": request_id,
        "plan": plan,
        "orchestrator_result": orch_result
    }
