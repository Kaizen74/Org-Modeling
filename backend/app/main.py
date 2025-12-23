"""
Organizational Design Workbench API

FastAPI application for parsing, analyzing, and transforming organizational structures.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from .models.database import init_db, close_db
from .api.routes import router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("ENVIRONMENT") == "production" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Organizational Design Workbench API...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Organizational Design Workbench",
    description="""
    Parse, analyze, and transform organizational structures.

    ## Features

    - **PowerPoint Parsing**: Parse org charts from PPTX files, including shapes outside the visible canvas
    - **CSV/Excel Import**: Import employee data from spreadsheets
    - **Validation**: Detect cycles, orphans, and structural issues
    - **Metrics**: Calculate span of control, hierarchy depth, and other KPIs
    - **AI Analysis**: Claude-powered structural analysis and recommendations
    - **Scenario Comparison**: Compare As-Is vs To-Be org structures

    ## Frameworks

    Based on Kates-Kesler and McKinsey organizational design frameworks.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Organizational Design Workbench API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") != "production",
    )
