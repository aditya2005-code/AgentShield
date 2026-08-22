from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure SQLAlchemy engine with pooling and connection pre-ping
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """
    FastAPI dependency that provides a transactional database session.
    Closes the session automatically upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
