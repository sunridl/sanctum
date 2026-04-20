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

# ---------------------------------------------------------------------------
# Test-support endpoints
# TODO: gate behind ENV=test before ever deploying this. In prod these are a
# security hole — anyone could create/delete users. For a local learning
# project where nothing is deployed, it's fine.
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str  # "therapist" or "psychiatrist"


@router.post("/users", status_code=201)
def create_user(data: CreateUserRequest):
    if data.email in USERS:
        raise HTTPException(status_code=409, detail="User already exists")
    USERS[data.email] = {
        "password": pwd_context.hash(data.password),
        "role": data.role,
    }
    return {"email": data.email, "role": data.role}


@router.delete("/users/{email}", status_code=204)
def delete_user(email: str):
    if email not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    del USERS[email]
    return None