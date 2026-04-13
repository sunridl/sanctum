from fastapi import FastAPI
from auth import router as auth_router
from clients import router as clients_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(clients_router)

@app.get("/")
def root():
    return {"message": "Sanctum is alive"}