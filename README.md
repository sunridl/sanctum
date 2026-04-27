# Sanctum

A clinical notes platform for therapists to securely manage client records and selectively share notes with consulting psychiatrists. Built as a portfolio project to demonstrate full-stack QA work — from finding real security bugs to writing the regression tests that lock them down.

## Why this project is interesting

While building Sanctum, I found and fixed three authorization bugs in the API:

- **Silent-success share** — the `share_client` endpoint silently accepted any string as a psychiatrist email, polluting application state with non-existent users. Same root-cause family as a payment-bypass bug I previously found in production at a different startup.
- **Two IDORs (Insecure Direct Object References)** in the notes endpoints — `GET` and `POST /clients/{id}/notes` authenticated the caller but never verified ownership of the target client. Any logged-in therapist could read or write notes on any other therapist's client by guessing IDs. This is the #1 issue on the OWASP API Security Top 10, also known as Broken Object Level Authorization (BOLA).

Each fix is paired with a **mutation-verified negative test** — meaning I deliberately revert the fix and confirm the test fails, then restore the fix and confirm it passes. A green test that wouldn't fail when the bug returns is false confidence; mutation verification is what makes the regression real.

## Stack

- **Backend:** FastAPI, JWT auth, in-memory state (database swap is intentionally deferred)
- **Frontend:** React + Vite
- **API tests:** pytest + httpx, fixture-driven state setup with teardown
- **UI tests:** Playwright (Python) with Page Object Model
- **CI:** GitHub Actions

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

Tests (backend and frontend must be running):

```bash
pip install -r requirements-dev.txt
playwright install
pytest tests_py/ -v
```

## What's tested

- **Authentication** — login success, login failure, token-based access
- **Authorization (IDOR/BOLA)** — cross-tenant isolation on read, write, and share endpoints; 404 (not 403) returned to prevent object enumeration
- **Client management** — creation, deletion, sharing with psychiatrist
- **UI flows** — login, role-based view rendering, fixture-driven state isolation

## Architecture notes

- Routers separated by domain (`auth`, `clients`, `notes`) so concerns don't bleed across modules.
- Tests own their state via pytest fixtures with uuid-based identifiers — no test depends on hardcoded backend data, so tests can run in parallel without collision.
- Page Object Model encapsulates UI structure: tests describe user intent, Page Objects describe mechanics. When the UI changes, only one file changes.

## What's next

- Notes flow: write/edit/delete UI, sharing notes between therapist and psychiatrist
- Signup with name capture and out-of-band psychiatrist verification
- Database persistence (SQLite → Postgres)
- Allure reporting integrated with CI
