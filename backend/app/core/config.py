import os
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    API_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str = Field(..., description="Connection URL for the PostgreSQL / Neon database")

    # CORS configuration
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]

    # Optional / Future extensions
    FRONTEND_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None

    # Gemini configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIM: int = 768  # dimension for gemini-embedding-001

    # ML Inference Configuration
    FRAUD_MODEL_PATH: str = "ml/models/fraud_model.joblib"
    FRAUD_PREPROCESSOR_PATH: str = "ml/models/preprocessor.joblib"
    FRAUD_METADATA_PATH: str = "ml/metadata/model_metadata.json"

    def resolve_ml_path(self, path_str: str) -> str:
        """
        Resolves a relative path to absolute by searching:
        1. Workspace root (parent of backend folder)
        2. Within backend folder
        Returns absolute path string.
        """
        from pathlib import Path
        p = Path(path_str)
        if p.is_absolute():
            return str(p)
        
        # Workspace root is parent of backend directory
        # config.py is at backend/app/core/config.py, so parent of backend is 4 levels up
        workspace_root = Path(__file__).resolve().parent.parent.parent.parent
        p_workspace = workspace_root / p
        if p_workspace.exists():
            return str(p_workspace)
            
        # Try relative to backend folder
        backend_root = Path(__file__).resolve().parent.parent.parent
        p_backend = backend_root / p
        if p_backend.exists():
            return str(p_backend)
            
        # Fallback to workspace root resolution
        return str(p_workspace)


    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must not be empty")
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        
        # Centralized normalization to ensure the modern psycopg (v3) driver is used
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
            
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

settings = Settings()
