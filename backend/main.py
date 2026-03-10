"""
ClaimSense.ai - FastAPI Application Entry Point

AI-powered medical insurance claims processing for the Indian market.
Catches administrative errors before claim submission, not after rejection.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()

    # Create upload directory if it doesn't exist
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory: %s", upload_path.resolve())

    # Log configuration summary
    logger.info("=" * 60)
    logger.info("ClaimSense.ai starting up")
    logger.info("Debug mode: %s", settings.DEBUG)
    logger.info("Gemini model: %s", settings.GEMINI_MODEL)
    logger.info("API key configured: %s", bool(settings.GEMINI_API_KEY))
    logger.info("Database: %s", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "not configured")
    logger.info("=" * 60)

    yield  # Application runs here

    logger.info("ClaimSense.ai shutting down")


# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ClaimSense.ai",
    description=(
        "AI-powered medical insurance claims processing for the Indian market. "
        "Catches administrative errors before claim submission - wrong codes, "
        "missing documents, policy rule violations - reducing the 17%% rejection rate."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware (allow frontend dev servers)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # React CRA / Next.js default
        "http://localhost:5173",       # Vite default
        "http://localhost:5174",       # Vite alternate
        "http://localhost:8080",       # Alternative dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint. Returns service status and configuration state."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "ClaimSense.ai",
        "version": "0.1.0",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": "ClaimSense.ai",
        "version": "0.1.0",
        "description": "Medical insurance claims processing API for the Indian market",
        "docs": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Route registration (conditional - loads modules as they are built)
# ---------------------------------------------------------------------------
def _try_include_router(module_path: str, prefix: str, tag: str):
    """
    Attempt to import and include a router module.
    Silently skips if the module doesn't exist yet (forward-compatible).
    """
    try:
        import importlib
        module = importlib.import_module(module_path)
        router = getattr(module, "router", None)
        if router:
            app.include_router(router, prefix=prefix, tags=[tag])
            logger.info("Loaded router: %s -> %s", module_path, prefix)
        else:
            logger.debug("Module %s has no 'router' attribute, skipping", module_path)
    except ImportError:
        logger.debug(
            "Router not available yet: %s (will be added in a later step)",
            module_path,
        )


# M1 - DocTriage Pipeline (upload and extraction)
_try_include_router("routes.upload", "/api", "M1 - DocTriage")

# M2 - Policy Rules Engine (validation)
_try_include_router("routes.validate", "/api", "M2 - Policy Engine")

# M3 - Clean Claim Guarantee (submission)
_try_include_router("routes.submit", "/api", "M3 - Clean Claim")

# Claims History (dashboard)
_try_include_router("routes.claims", "/api", "Claims History")


# ---------------------------------------------------------------------------
# Run with: python main.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
