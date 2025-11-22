"""
Main application entry point.

Initializes FastAPI app, configures middleware, mounts static files,
and registers all API routers from views.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import time

from .db import engine, Base

# Import all routers from views
from .views import (
    health_router,
    observations_router,
    alerts_router,
    heatmap_router,
    data_generation_router,
    mobile_router,
)

# Create tables with retry logic
max_retries = 5
retry_delay = 2

for attempt in range(max_retries):
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"⚠ Database connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        else:
            print(f"✗ Failed to connect to database after {max_retries} attempts")
            raise

# Initialize FastAPI application
app = FastAPI(
    title="Hemogram Monitoring API",
    version="0.1.0",
    description="Sistema de Monitoramento de Hemogramas - API para recepção, análise e alertas"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Register routers
app.include_router(health_router)
app.include_router(observations_router)
app.include_router(alerts_router)
app.include_router(heatmap_router)
app.include_router(data_generation_router)
app.include_router(mobile_router)

# Application startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    print("=" * 60)
    print("🚀 Hemogram Monitoring System Started")
    print("=" * 60)
    print(f"📍 API Docs: http://localhost:8000/docs")
    print(f"🗺️  Heatmap: http://localhost:8000")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    print("=" * 60)
    print("👋 Hemogram Monitoring System Shutting Down")
    print("=" * 60)
