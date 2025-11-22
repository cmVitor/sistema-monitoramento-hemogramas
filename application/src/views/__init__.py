"""
Views package for organizing API endpoints.
"""
from .health import router as health_router
from .observations import router as observations_router
from .alerts import router as alerts_router
from .heatmap import router as heatmap_router
from .data_generation import router as data_generation_router
from .mobile import mobile_router

__all__ = [
    "health_router",
    "observations_router",
    "alerts_router",
    "heatmap_router",
    "data_generation_router",
    "mobile_router",
]
