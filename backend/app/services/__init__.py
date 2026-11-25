"""
TRIPPY Backend — Services Package

Exports the LLM provider and location verifier eagerly.
The orchestrator is lazy-loaded via __getattr__ to break the circular
import chain:  app.agents.__init__ -> app.agents.budget -> app.services
-> app.services.__init__ -> app.services.orchestrator -> app.agents.crew
-> app.agents.budget (partially initialized).
"""

from .llm_provider import LLMProviderService, llm_service
from .location_verifier import LocationVerifier, location_verifier

__all__ = [
    "LLMProviderService",
    "LocationVerifier",
    "TripOrchestratorService",
    "llm_provider",
    "location_verifier",
    "trip_service",
]

_LAZY_ATTRS = {"TripOrchestratorService", "trip_service"}


def __getattr__(name: str):
    """Lazily expose orchestrator exports without triggering circular imports."""
    if name in _LAZY_ATTRS:
        try:
            from . import orchestrator

            return getattr(orchestrator, name)
        except ImportError:
            raise AttributeError(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")