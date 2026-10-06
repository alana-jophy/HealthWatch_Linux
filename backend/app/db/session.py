from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from loguru import logger
from app.core.config import settings

# Create SQLAlchemy synchronous engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

# Create session maker factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """Check database health, query latency, and PostGIS extension status."""
    import time
    start_time = time.time()
    try:
        with engine.connect() as conn:
            # Check basic SQL execution
            conn.execute(text("SELECT 1"))

            # Check PostGIS extension & version
            postgis_version = None
            postgis_full = None
            try:
                res_ver = conn.execute(text("SELECT PostGIS_Version();"))
                row_ver = res_ver.fetchone()
                if row_ver:
                    postgis_version = str(row_ver[0])

                res_full = conn.execute(text("SELECT PostGIS_Full_Version();"))
                row_full = res_full.fetchone()
                if row_full:
                    postgis_full = str(row_full[0])
            except Exception as e:
                postgis_version = f"Not loaded: {str(e)}"

            latency_ms = round((time.time() - start_time) * 1000, 2)

            return {
                "status": "connected",
                "postgis_installed": postgis_version is not None and "not loaded" not in str(postgis_version).lower(),
                "postgis_version": postgis_version,
                "postgis_full_version": postgis_full,
                "latency_ms": latency_ms,
            }
    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Database health check failed: {exc}")
        return {
            "status": "disconnected",
            "error": str(exc),
            "postgis_installed": False,
            "postgis_version": None,
            "postgis_full_version": None,
            "latency_ms": latency_ms,
        }

