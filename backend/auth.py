from enum import Enum
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext

router = APIRouter(prefix="/auth")

SECRET_KEY = "sanctum-secret-do-not-share"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Role(str, Enum):
    therapist = "therapist"
    psychiatrist = "psychiatrist"


USERS = {
    "therapist@sanctum.com": {
        "password": pwd_context.hash("secret123"),
        "role": "therapist",
        "first_name": "Sarah",
        "last_name": "Hill",
    },
    "psych@sanctum.com": {
        "password": pwd_context.hash("secret123"),
        "role": "psychiatrist",
        "first_name": "Pat",
        "last_name": "Chen",
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
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
    }


# ---------------------------------------------------------------------------
# Public signup
# ---------------------------------------------------------------------------
# NOTE: psychiatrist self-selection is a deliberate demo-time shortcut.
# In a real deployment, psychiatrist accounts would require out-of-band
# verification (license check) — see README "What's next".

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    role: Role


@router.post("/signup", status_code=201)
def signup(data: SignupRequest):
    if data.email in USERS:
        raise HTTPException(status_code=409, detail="Email already registered")

    USERS[data.email] = {
        "password": pwd_context.hash(data.password),
        "role": data.role.value,
        "first_name": data.first_name,
        "last_name": data.last_name,
    }
    token = create_token(data.email, data.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": data.role.value,
        "first_name": data.first_name,
        "last_name": data.last_name,
    }


# ---------------------------------------------------------------------------
# Psychiatrist lookup — used by the share-confirmation flow on the frontend
# ---------------------------------------------------------------------------
# Therapist-only by design: only therapists need to look up psychiatrists
# (they're the ones who share clients), and limiting access keeps the
# email-probe surface narrow. 404 (not 403) for non-psychiatrist or
# unknown emails matches the codebase's anti-enumeration convention.

security = HTTPBearer()


def _decode_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    # NOTE: duplicated with clients.py / notes.py — refactor candidate.
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not USERS.get(payload.get("sub")):
        raise HTTPException(status_code=401, detail="User no longer exists")
    return payload


@router.get("/psychiatrists/{email}")
def lookup_psychiatrist(email: str, user: dict = Depends(_decode_token)):
    if user.get("role") != "therapist":
        raise HTTPException(status_code=404, detail="Psychiatrist not found")

    target = USERS.get(email)
    if not target or target["role"] != "psychiatrist":
        raise HTTPException(status_code=404, detail="Psychiatrist not found")

    return {
        "email": email,
        "first_name": target.get("first_name", ""),
        "last_name": target.get("last_name", ""),
    }


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
    first_name: str = ""
    last_name: str = ""


@router.post("/users", status_code=201)
def create_user(data: CreateUserRequest):
    if data.email in USERS:
        raise HTTPException(status_code=409, detail="User already exists")
    USERS[data.email] = {
        "password": pwd_context.hash(data.password),
        "role": data.role,
        "first_name": data.first_name,
        "last_name": data.last_name,
    }
    return {"email": data.email, "role": data.role}


@router.delete("/users/{email}", status_code=204)
def delete_user(email: str, caller: dict = Depends(_decode_token)):
    # Self-delete only: a user may only delete their own account. Without
    # this check, the endpoint was open to anyone with a curl command —
    # an unauthenticated attacker could wipe accounts at will.
    # 404 (not 403) hides the role/identity boundary, matching the
    # codebase's anti-enumeration convention.
    if caller.get("sub") != email:
        raise HTTPException(status_code=404, detail="User not found")

    user = USERS.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cascade-clean the share graph so no orphaned references remain.
    # Lazy import: clients.py imports USERS from this module, so a top-level
    # `from clients import CLIENTS` would create a circular import.
    # TODO: a future refactor could move CLIENTS to a shared state module.
    from clients import CLIENTS

    if user["role"] == "psychiatrist":
        # Any therapist's client that was shared with this psychiatrist
        # must have its shared_with field cleared.
        for owner_email, client_list in CLIENTS.items():
            if owner_email == email:
                continue
            for c in client_list:
                if c.get("shared_with") == email:
                    c["shared_with"] = None
    elif user["role"] == "therapist":
        # The therapist's clients have no owner anymore; cascade-remove
        # them from every psychiatrist's list so vanished clients don't
        # linger in psychiatrist views.
        owned_ids = {c["id"] for c in CLIENTS.get(email, [])}
        for other_email, client_list in CLIENTS.items():
            if other_email == email:
                continue
            client_list[:] = [c for c in client_list if c["id"] not in owned_ids]

        # Cascade-clean notes for every deleted client so they don't sit
        # orphaned in memory. Same lazy-import rationale as above.
        from notes import NOTES
        for cid in owned_ids:
            NOTES.pop(cid, None)

    # Drop the deleted user's own CLIENTS entry (their owned clients if a
    # therapist; their shared-copy view if a psychiatrist).
    CLIENTS.pop(email, None)

    del USERS[email]
    return None