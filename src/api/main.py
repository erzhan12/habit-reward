"""FastAPI application factory and configuration."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import api_settings
from src.api.exceptions import setup_exception_handlers
from src.api.middleware.logging import LoggingMiddleware
from src.api.v1.routers import auth, users, habits, rewards, habit_logs, streaks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("Starting Habit Reward API")
    yield
    # Shutdown
    logger.info("Shutting down Habit Reward API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Habit Reward API",
        description="REST API for the Habit Reward tracking system",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom logging middleware
    app.add_middleware(LoggingMiddleware)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include routers
    app.include_router(
        auth.router,
        prefix="/v1/auth",
        tags=["Authentication"]
    )
    app.include_router(
        users.router,
        prefix="/v1/users",
        tags=["Users"]
    )
    app.include_router(
        habits.router,
        prefix="/v1/habits",
        tags=["Habits"]
    )
    app.include_router(
        rewards.router,
        prefix="/v1/rewards",
        tags=["Rewards"]
    )
    app.include_router(
        habit_logs.router,
        prefix="/v1/habit-logs",
        tags=["Habit Logs"]
    )
    app.include_router(
        streaks.router,
        prefix="/v1/streaks",
        tags=["Streaks"]
    )

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}

    return app


# Create the application instance
app = create_app()
