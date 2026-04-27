from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from auth import USERS

class ClientCreate(BaseModel):
    first_name: str
    last_name: str


router = APIRouter(prefix="/clients")

SECRET_KEY = "sanctum-secret-do-not-share"
ALGORITHM = "HS256"

CLIENTS: dict[str, list] = {
    "therapist@sanctum.com": [
        {"id": 1, "first_name": "Carol", "last_name": "Smith", "shared_with": None},
        {"id": 2, "first_name": "David", "last_name": "Jones", "shared_with": None},
    ],
    "psych@sanctum.com": [],
}
client_id_counter = 3

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/")
def get_clients(user: dict = Depends(get_current_user)):
    email = user["sub"]
    return CLIENTS.get(email, [])

@router.post("/")
def create_client(data: ClientCreate, user: dict = Depends(get_current_user)):
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
    email = user["sub"]

    # Only allow the owner (therapist) to delete
    owner_list = CLIENTS.get(email, [])
    client = next((c for c in owner_list if c["id"] == client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Remove from every list (owner + anyone it was shared with)
    for clients_list in CLIENTS.values():
        clients_list[:] = [c for c in clients_list if c["id"] != client_id]

    return None