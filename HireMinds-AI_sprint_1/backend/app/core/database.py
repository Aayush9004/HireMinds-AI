"""
Database session management and engine configuration using SQLAlchemy 2.0
"""
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings

# Create SQLAlchemy engine with connection pooling and health-check ping
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# Session factory for generating request-scoped database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base for all application models.
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and guarantees proper session cleanup upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """
    Utility function to verify active database connectivity.
    Returns status and diagnostic details.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            return {
                "connected": result == 1,
                "database": settings.DB_NAME,
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
            }
    except Exception as exc:
        return {
            "connected": False,
            "error": str(exc),
            "database": settings.DB_NAME,
        }
