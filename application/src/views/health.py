"""
Health check and root endpoints.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/")
def root():
    """Serve the heatmap visualization page."""
    static_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static"
    )
    return FileResponse(os.path.join(static_path, "heatmap.html"))
