import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="AgentShield API",
    description="Centralized AI action-control platform for financial AI agents",
    version="0.1.0"
)

# CORS configurations
origins_env = os.getenv("CORS_ORIGINS")
if origins_env:
    import json
    try:
        origins = json.loads(origins_env)
    except Exception:
        origins = [origins_env]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthStatus(BaseModel):
    status: str
    day: int

@app.get("/health", response_model=HealthStatus)
def health_check():
    return HealthStatus(status="ok", day=1)
