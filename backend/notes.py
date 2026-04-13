from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

router = APIRouter(prefix="/clients")

SECRET_KEY = "sanctum-secret-do-not-share"
ALGORITHM = "HS256"
security = HTTPBearer()

NOTES: dict[int, list] = {
    1: [
        {"id": 1, "content": "Carol is making progress", "is_private": True, "author": "therapist@sanctum.com", "role": "therapist"},
        {"id": 2, "content": "Carol approved for group therapy", "is_private": False, "author": "therapist@sanctum.com", "role": "therapist"},
    ]
}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

class NoteCreate(BaseModel):
    content: str
    is_private: bool = True

@router.post("/{client_id}/notes")
def create_note(client_id: int, data: NoteCreate, user: dict = Depends(get_current_user)):
    global note_id_counter
    note = {
        "id": note_id_counter,
        "content": data.content,
        "is_private": data.is_private,
        "author": user["sub"],
        "role": user["role"]
    }
    NOTES.setdefault(client_id, []).append(note)
    note_id_counter += 1
    return note

@router.get("/{client_id}/notes")
def get_notes(client_id: int, user: dict = Depends(get_current_user)):
    notes = NOTES.get(client_id, [])
    if user["role"] == "psychiatrist":
        notes = [n for n in notes if not n["is_private"]]
    return notes