from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

class ClientCreate(BaseModel):
    first_name: str
    last_name: str


router = APIRouter(prefix="/clients")

SECRET_KEY = "sanctum-secret-do-not-share"
ALGORITHM = "HS256"

CLIENTS = {
    "therapist@sanctum.com": [],
    "psych@sanctum.com": [],
}
client_id_counter = 1

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
    new_client = {"id": client_id_counter, "first_name": data.first_name, "last_name": data.last_name}
    CLIENTS[email].append(new_client)
    client_id_counter += 1
    return new_client

class ShareRequest(BaseModel):
    psychiatrist_email: str

@router.post("/{client_id}/share")
def share_client(client_id: int, data: ShareRequest, user: dict = Depends(get_current_user)):
    email = user["sub"]
    # Find the client in therapist's list
    therapist_clients = CLIENTS.get(email, [])
    client = next((c for c in therapist_clients if c["id"] == client_id), None)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    # Add to psychiatrist's list
    if data.psychiatrist_email not in CLIENTS:
        CLIENTS[data.psychiatrist_email] = []
    CLIENTS[data.psychiatrist_email].append(client)
    return {"message": f"Client shared with {data.psychiatrist_email}"}