from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel, StringConstraints
from auth import USERS, SECRET_KEY, ALGORITHM

# Strips leading/trailing whitespace, then requires at least 1 char.
# Catches both "" and "   " in one declaration; stored value is stripped
# so we don't persist surprise whitespace.
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ClientCreate(BaseModel):
    first_name: NonEmptyStr
    last_name: NonEmptyStr


router = APIRouter(prefix="/clients")

CLIENTS: dict[str, list] = {}
client_id_counter = 1

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # NOTE: this auth dependency is duplicated in notes.py and auth.py
    # (_decode_token). Future refactor: extract into a shared module.
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Reject tokens whose subject no longer exists — handles the case where
    # a user account was deleted while a valid JWT was still in flight.
    if not USERS.get(payload.get("sub")):
        raise HTTPException(status_code=401, detail="User no longer exists")
    return payload

def _enrich_shared_with(client: dict) -> dict:
    """Expand shared_with from a bare email string into an object the
    frontend can render directly: {email, first_name, last_name}.
    Storage stays normalized (one email per client); the join happens at
    read time. Falls back to empty name fields if the psychiatrist user
    record is missing — defensive against deleted users."""
    psych_email = client.get("shared_with")
    if not psych_email:
        return {**client, "shared_with": None}
    psych = USERS.get(psych_email, {})
    return {
        **client,
        "shared_with": {
            "email": psych_email,
            "first_name": psych.get("first_name", ""),
            "last_name": psych.get("last_name", ""),
        },
    }


@router.get("/")
def get_clients(user: dict = Depends(get_current_user)):
    email = user["sub"]
    return [_enrich_shared_with(c) for c in CLIENTS.get(email, [])]

@router.post("/")
def create_client(data: ClientCreate, user: dict = Depends(get_current_user)):
    # Therapist-only: clients are a therapist concept. A psychiatrist-
    # created client could never be shared, viewed, or annotated by
    # anyone else — a domain-incoherent record. 404 hides the role gate.
    if user["role"] != "therapist":
        raise HTTPException(status_code=404, detail="Client not found")

    global client_id_counter
    email = user["sub"]
    new_client = {
        "id": client_id_counter,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "shared_with": None,
    }
    CLIENTS.setdefault(email, []).append(new_client)
    client_id_counter += 1
    return new_client

class ShareRequest(BaseModel):
    psychiatrist_email: str

@router.post("/{client_id}/share")
def share_client(client_id: int, data: ShareRequest, user: dict = Depends(get_current_user)):
    # Therapist-only: only the client owner may initiate a share. Without
    # this guard, a psychiatrist with a shared client could try to forward-
    # share it; the request would still fail (409 from the existing-share
    # check), but 409 leaks "you have access to this client" — defense in
    # depth says reject earlier with 404.
    if user["role"] != "therapist":
        raise HTTPException(status_code=404, detail="Client not found")

    email = user["sub"]

    # Validate target is a real registered psychiatrist
    target = USERS.get(data.psychiatrist_email)
    if not target or target["role"] != "psychiatrist":
        raise HTTPException(status_code=404, detail="Psychiatrist not found")

    # Find the client in therapist's list
    therapist_clients = CLIENTS.get(email, [])
    client = next((c for c in therapist_clients if c["id"] == client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # A client is shared with at most one psychiatrist. The UI hides the
    # share form once a share exists; the 409 here is defense-in-depth
    # against API-level misuse and races.
    if client.get("shared_with"):
        raise HTTPException(
            status_code=409,
            detail=f"Client is already shared with {client['shared_with']}",
        )

    client["shared_with"] = data.psychiatrist_email
    CLIENTS.setdefault(data.psychiatrist_email, []).append(client)
    return {"message": f"Client shared with {data.psychiatrist_email}"}


@router.delete("/{client_id}/share", status_code=204)
def unshare_client(client_id: int, user: dict = Depends(get_current_user)):
    # Therapist-only: only the share originator may dissolve the share.
    # Without this guard, a psychiatrist could clear shared_with on their
    # own access, which silently mutates the therapist's view of the
    # client. Sharing is initiated by the therapist; revocation is too.
    if user["role"] != "therapist":
        raise HTTPException(status_code=404, detail="Client not found")

    email = user["sub"]

    # Owner check — prevents IDOR (mirrors share_client). Foreign clients
    # get 404, not 403, so the endpoint can't be used to enumerate IDs.
    therapist_clients = CLIENTS.get(email, [])
    client = next((c for c in therapist_clients if c["id"] == client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    psych_email = client.get("shared_with")
    if psych_email:
        client["shared_with"] = None
        psych_list = CLIENTS.get(psych_email, [])
        psych_list[:] = [c for c in psych_list if c["id"] != client_id]

    # Idempotent: 204 even if the client wasn't shared.
    return None

@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, user: dict = Depends(get_current_user)):
    # Therapist-only: psychiatrists access shared clients read-only.
    # Without this guard, a psychiatrist with a shared client could DELETE
    # the underlying record (the cascade-removal would wipe the original
    # from the therapist's list too — read access leaking into delete).
    if user["role"] != "therapist":
        raise HTTPException(status_code=404, detail="Client not found")

    email = user["sub"]
    owner_list = CLIENTS.get(email, [])
    client = next((c for c in owner_list if c["id"] == client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Remove from every list (owner + anyone it was shared with)
    for clients_list in CLIENTS.values():
        clients_list[:] = [c for c in clients_list if c["id"] != client_id]

    # Cascade-clean the notes for this client. Lazy import to avoid the
    # circular dependency: notes.py already imports CLIENTS from here.
    from notes import NOTES
    NOTES.pop(client_id, None)

    return None