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
from app.api.agentshield import router as agentshield_router
from app.api.rag import router as rag_router
from app.api.fraud import router as fraud_router

app.include_router(agents_router, prefix="/api/v1")
app.include_router(merchants_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(proposals_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(audit_logs_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(agentshield_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(fraud_router, prefix="/api/v1")

from fastapi import Request
from fastapi.responses import JSONResponse
from app.ml.inference.exceptions import (
    FraudModelArtifactNotFoundError,
    FraudModelLoadError,
    FraudModelPredictionError,
)

@app.exception_handler(FraudModelArtifactNotFoundError)
async def fraud_model_artifact_not_found_handler(request: Request, exc: FraudModelArtifactNotFoundError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Fraud ML service unavailable: model artifacts not found."},
    )

@app.exception_handler(FraudModelLoadError)
async def fraud_model_load_error_handler(request: Request, exc: FraudModelLoadError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Fraud ML service unavailable: model failed to load."},
    )

@app.exception_handler(FraudModelPredictionError)
async def fraud_model_prediction_error_handler(request: Request, exc: FraudModelPredictionError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Fraud prediction execution failed."},
    )
