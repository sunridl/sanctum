# Sanctum

A clinical notes platform for therapists to securely manage client records and selectively share notes with consulting psychiatrists. Built as a portfolio project to demonstrate full-stack QA work — from finding real security bugs to writing the regression tests that lock them down.

## Why this project is interesting

While building Sanctum, I found and fixed a series of authorization and lifecycle bugs in the API. Each fix is paired with a **mutation-verified test**: I deliberately revert the fix, confirm the test fails on the broken code, then restore the fix and confirm it passes. A green test that wouldn't catch the regression is false confidence; mutation verification is what makes the test load-bearing.

### Authorization (IDOR / BOLA — OWASP API Security #1)

- **Silent-success share** — `share_client` accepted any string as a psychiatrist email, polluting state with non-existent users. Same root-cause family as a payment-bypass bug I previously found in production at a different startup.
- **Notes IDORs** — `GET` and `POST /clients/{id}/notes` authenticated the caller but never verified ownership of the target client. Any logged-in therapist could read or write notes on any other therapist's client by guessing IDs.
- **Psychiatrist could destroy shared clients** — `DELETE /clients/{id}` found the client in *the caller's* list (which for a psychiatrist contains shared copies), then cascaded a removal across every list. Read access via share leaked into delete access.
- **Psychiatrist could unshare without therapist consent** — same shape: share state was mutable by the recipient, not just the originator.

### Defense-in-depth gaps (UI hides ≠ backend rejects)

- **Psychiatrist could create private notes via API** — the UI hid the toggle, but the API accepted `is_private: true`. Without a backend role check, a private note created by a psychiatrist becomes invisible to themselves on the next reload (the GET filter hides it).
- **Psychiatrist could create their own clients** — domain-incoherent records: a "client" with no therapist owner could never be shared, viewed by anyone else, or have notes that reach a clinician.

### Lifecycle integrity

- **Anyone could delete any user via curl** — the `/auth/users` admin endpoint had zero authentication. Tightened to self-delete only (caller's JWT subject must equal the path email).
- **Deleted user's JWT still worked** — the auth dependency only verified signature; it didn't check whether the user still existed in `USERS`. The deleted user could keep accessing their orphaned client list.
- **Cascade leaks on user deletion** — deleting a psychiatrist left therapists' clients pointing at vanished accounts; deleting a therapist left their clients lingering in psychiatrist views. Now both directions clean up the share graph.

### Convention

Authorization rejections return **404, not 403**, consistently across the codebase. The reasoning is in inline comments and reinforced by tests asserting `status == 404` on cross-tenant attempts: 404 hides the role/identity gate from a probing attacker, so they can't even tell the resource exists.

## Stack

- **Backend:** FastAPI, JWT auth, Pydantic v2 (`Annotated[str, StringConstraints]` for input validation)
- **Frontend:** React 19 + Vite, React Router v7, Context API for auth, sessionStorage for token persistence
- **API tests:** pytest + httpx, parametrised validation matrices, fixture-driven setup with self-delete teardown
- **UI tests:** Playwright (Python) with Page Object Model
- **CI:** GitHub Actions (Dockerised backend + Vite + Playwright)

## Run it locally

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Tests (backend on `:8000` and frontend on `:5173` must both be running):

```bash
pip install -r backend/requirements-dev.txt
playwright install
pytest tests_py/ -v
```

## What's tested

**79 tests** across 12 files, organised by domain (no junk-drawer file).

| Area | Files | What's covered |
|---|---|---|
| **Auth lifecycle** | `test_auth.py`, `test_auth_ui.py` | deleted-user 401, self-delete only, cascade cleanup on deletion (both roles), deletion-message rendered on dashboard |
| **Signup** | `test_signup.py`, `test_signup_ui.py` | email format, password length, role enum, name fields, duplicate-email 409, signup→login round-trip, logout-after-signup regression |
| **Login / dashboard UI** | `test_dashboard.py` | per-role login, login failure stays on screen, role-based client listing |
| **Client CRUD** | `test_clients.py` | happy paths (POST/GET/DELETE), role guards, IDOR (therapist-vs-therapist), cascade on shared-client delete, input validation (empty + whitespace) |
| **Sharing** | `test_share.py`, `test_share_ui.py` | lookup endpoint × 5 (200 / 404 unknown / 404 therapist email / 404 wrong role / 401 unauth), double-share rejection (same and different psychiatrist), forward-share rejection, idempotent unshare, two-step share-confirmation UX, cancel returns to input |
| **Notes** | `test_notes.py`, `test_notes_ui.py` | privacy-by-default model, backend role-filter, attribution fields (author + first/last name + role), IDOR (R/W), psych can't create private notes, psych UI hides toggle and badge (mutation-verified), input validation |
| **Infrastructure smoke** | `test_smoke.py` | frontend serves, fixtures wire up cleanly |

## Architecture notes

- **Routers separated by domain** (`auth`, `clients`, `notes`) — concerns don't bleed across modules.
- **Frontend split into pages + contexts** — `App.jsx` is a routing shell with `RequireAuth` guards; per-page logic lives in `pages/{Login,Dashboard,Client}Page.jsx`; auth state lives in `contexts/AuthContext.jsx` with sessionStorage persistence so deep links survive a page refresh.
- **Privacy-by-default for notes** — the UI toggle reads "Shared (visible to psychiatrist)" rather than "Private," so an unchecked default produces a private note. The "Shared" badge marks the *exception*, not the default. Renders only on the therapist's view (psychiatrists by definition only see shared notes).
- **Two-step share with confirmation** — entering an email triggers a lookup that returns the psychiatrist's name; the therapist confirms before the actual share commits. Catches typos before they create a wrong-person share, which is rough to undo.
- **Tests own their state via pytest fixtures** with uuid-based identifiers — no test depends on hardcoded backend data; tests can run in parallel without collision.
- **Page Object Model encapsulates UI structure** — tests describe user intent (`client_page.share_with(email)`); Page Objects describe mechanics. When the UI changes, one file changes.
- **Test files split by domain** — `test_<domain>.py` for API, `test_<domain>_ui.py` for Playwright. Reading the file name tells you what kind of test you're about to read.
- **Mutation verification for security-critical tests** — for every role guard, IDOR check, and role-based filter, I deliberately broke the code, confirmed the test failed, then restored. The test's authority comes from being caught failing on real broken code.

## Intentional shortcuts (with reasoning)

A few decisions that look like rough edges in code review — flagging the reasoning so it's clear they're choices, not oversights:

- **JWT in `sessionStorage`** rather than HTTP-only cookies — readable by JS (XSS exposure), but lets deep links and refreshes work without the cookie + CSRF infrastructure. Documented inline in `AuthContext.jsx`.
- **In-memory state** (no database) — keeps the demo runnable without setup. The cascade-cleanup logic on user deletion uses dict mutation; the same logic translates directly to `ON DELETE CASCADE` on a real DB.
- **Test-only `/auth/users` admin endpoint** — kept open (no auth) so fixtures can create users with arbitrary roles. Real signups go through `/auth/signup`, which has full validation. Marked clearly with a comment.
- **Notes orphaned on client deletion** — flagged in code with `# TODO`; the unreachable rows in NOTES are inert in memory but would need a foreign-key cascade in a real DB.
- **Three duplicated `get_current_user` definitions** (in `auth.py`, `clients.py`, `notes.py`) — flagged with a refactor comment in each. Extracting to a shared module would have inflated multiple bug-fix diffs; left as a focused future task.

## What's next

- Database persistence (SQLite → Postgres) with cascade FKs replacing the manual cleanup logic
- HTTP-only cookies for auth, removing the sessionStorage XSS surface
- Notes edit/delete (currently list + create only)
- ClientPage 401 handling — the dashboard shows the deletion message; ClientPage doesn't yet (it crashes when `loadClient()` hits a 401 since the response body isn't an array)
- Allure reporting integrated with CI
