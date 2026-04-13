from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth")

# Fake users for now — we'll make this real later
USERS = {
    "therapist@sanctum.com": {"password": "secret123", "role": "therapist"},
    "psych@sanctum.com":     {"password": "secret123", "role": "psychiatrist"},
}

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(data: LoginRequest):
    user = USERS.get(data.email)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": f"fake-token-{data.email}", "role": user["role"]}