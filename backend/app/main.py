"""
Org Design Analyzer - FastAPI Backend

A lightweight organizational design analyzer that:
1. Parses CSV org data and calculates 6 core metrics
2. Provides AI-powered analysis with structured insights categorization
3. Runs on consultant laptops (SQLite, no Docker required)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models.database import init_db, close_db
from .api import settings, grades, org_data, metrics, ai_analysis

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Org Design Analyzer",
    description="Analyze organizational structures and get AI-powered insights",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(settings.router)
app.include_router(grades.router)
app.include_router(org_data.router)
app.include_router(metrics.router)
app.include_router(ai_analysis.router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "org-design-analyzer"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Org Design Analyzer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
