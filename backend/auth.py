from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

router = APIRouter(prefix="/auth")

SECRET_KEY = "sanctum-secret-do-not-share"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS = {
    "therapist@sanctum.com": {
        "password": pwd_context.hash("secret123"),
        "role": "therapist"
    },
    "psych@sanctum.com": {
        "password": pwd_context.hash("secret123"),
        "role": "psychiatrist"
    },
}

class LoginRequest(BaseModel):
    email: str
    password: str

def create_token(email: str, role: str) -> str:
    payload = {
        "sub": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(data: LoginRequest):
    user = USERS.get(data.email)
    if not user or not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(data.email, user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}