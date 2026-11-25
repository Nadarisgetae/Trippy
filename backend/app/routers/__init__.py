from .health import router as health_router
from .stages import router as stages_router
from .trips import router as trips_router

__all__ = ["health_router", "stages_router", "trips_router"]
