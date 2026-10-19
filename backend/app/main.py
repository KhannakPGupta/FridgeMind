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


from backend.app.api.health import router as health_router
from backend.app.api.ingredients import router as ingredients_router
from backend.app.api.recipes import router as recipes_router


# Include API Routers
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(ingredients_router, prefix=settings.API_V1_PREFIX)
app.include_router(recipes_router, prefix=settings.API_V1_PREFIX)




@app.get("/")
async def root():
    """Root endpoint redirecting to docs or health."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
