from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from auth import USERS
from clients import CLIENTS

router = APIRouter(prefix="/clients")

SECRET_KEY = "sanctum-secret-do-not-share"
ALGORITHM = "HS256"
security = HTTPBearer()
note_id_counter = 1

NOTES: dict[int, list] = {
    1: [
        {"id": 1, "content": "Carol is making progress", "is_private": True, "author": "therapist@sanctum.com", "role": "therapist"},
        {"id": 2, "content": "Carol approved for group therapy", "is_private": False, "author": "therapist@sanctum.com", "role": "therapist"},
    ]
}

def _user_owns_client(user: dict, client_id: int) -> bool:
    """True if the authenticated user has this client in their own list —
    i.e. they're either the therapist who created them, or a psychiatrist
    the client was shared with. Same check works for both roles."""
    email = user["sub"]
    user_clients = CLIENTS.get(email, [])
    return any(c["id"] == client_id for c in user_clients)


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
    if not _user_owns_client(user, client_id):
        raise HTTPException(status_code=404, detail="Client not found")

    # Private notes are a therapist-only concept — psychiatrists can't see them
    # (the GET endpoint filters them out), so they shouldn't be able to create
    # them either. 404 (not 403) keeps role boundaries opaque to ID-probing
    # attackers, matching the codebase's anti-enumeration convention.
    if data.is_private and user["role"] != "therapist":
        raise HTTPException(status_code=404, detail="Client not found")

    note = {
        "id": note_id_counter,
        "content": data.content,
        "is_private": data.is_private,
        "author": user["sub"],
        "role": user["role"],
    }
    NOTES.setdefault(client_id, []).append(note)
    note_id_counter += 1
    return note


@router.get("/{client_id}/notes")
def get_notes(client_id: int, user: dict = Depends(get_current_user)):
    if not _user_owns_client(user, client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    notes = NOTES.get(client_id, [])
    if user["role"] == "psychiatrist":
        notes = [n for n in notes if not n["is_private"]]
    # Enrich each note with the author's display name. Looked up at read
    # time rather than stamped at write time — for a clinical app, the
    # audit-log-correct choice is denormalize-on-write so name changes
    # don't rewrite history. Acceptable here because the demo has no
    # name-change feature; flagging for a future migration.
    return [
        {
            **note,
            "author_first_name": USERS.get(note["author"], {}).get("first_name", ""),
            "author_last_name": USERS.get(note["author"], {}).get("last_name", ""),
        }
        for note in notes
    ]