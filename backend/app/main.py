"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.data.seed_data import seed_database
from backend.app.api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events on startup and shutdown."""
    logger.info("Starting %s v%s in %s mode", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)
    logger.info("CORS origins allowed: %s", settings.CORS_ORIGINS)
    
    # Initialize and seed database if necessary
    seed_database()

    if settings.GEMINI_API_KEY:
        logger.info("Google Gemini API is configured.")
    else:
        logger.warning("Google Gemini API key is not set. Offline catalog and rule-based matching will be used.")
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API and ML Services for FridgeMind recipe recommendation and ingredient recognition.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Structured error response for schema validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "The submitted payload does not match the expected schema.",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler ensuring clean JSON output."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
        },
    )


from pathlib import Path
from typing import Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

from backend.app.api.health import router as health_router
from backend.app.api.ingredients import router as ingredients_router
from backend.app.api.recipes import router as recipes_router


# Include API Routers first so they take route priority
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(ingredients_router, prefix=settings.API_V1_PREFIX)
app.include_router(recipes_router, prefix=settings.API_V1_PREFIX)


def get_frontend_dist() -> Optional[Path]:
    """Locate pre-built frontend distribution directory across local and container environments."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "dist",  # repo root / dist
        Path(__file__).resolve().parent.parent.parent / "dist",         # backend / dist
        Path("/app/dist"),                                             # Docker standard
        Path("/app/frontend_dist"),
    ]
    for p in candidates:
        if p.is_dir() and (p / "index.html").is_file():
            return p
    return None


frontend_dist = get_frontend_dist()

if frontend_dist:
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def root(request: Request):
        """Serve SPA index.html for web browsers, or JSON metadata for API clients."""
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return FileResponse(frontend_dist / "index.html")
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve compiled frontend static files or fallback to index.html for client-side routing."""
        if full_path.startswith("api") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint returning API metadata when frontend dist is not built."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }


