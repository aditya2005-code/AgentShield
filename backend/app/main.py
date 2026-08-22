from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.health import router as health_router

app = FastAPI(
    title="AgentShield API",
    description="Centralized AI action-control platform for financial AI agents",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)

from app.api.agents import router as agents_router
from app.api.merchants import router as merchants_router
from app.api.transactions import router as transactions_router
from app.api.proposals import router as proposals_router
from app.api.decisions import router as decisions_router
from app.api.audit_logs import router as audit_logs_router
from app.api.demo import router as demo_router

app.include_router(agents_router, prefix="/api/v1")
app.include_router(merchants_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(proposals_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(audit_logs_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
