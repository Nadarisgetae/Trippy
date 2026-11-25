"""
TRIPPY Backend — Agents Package

Exports the five specialist agents and the Crew orchestrator.
Google ADK workflow exports are lazy-loaded via __getattr__ to avoid
eager google.adk import failures and circular import loops.
"""

from .base import TrippyAgent
from .budget import BudgetAgent
from .crew import TrippyCrew
from .destination import DestinationAgent
from .itinerary import ItineraryAgent
from .stay_activity import StayActivityAgent
from .transport import TransportAgent

__all__ = [
    "BudgetAgent",
    "DestinationAgent",
    "ItineraryAgent",
    "StayActivityAgent",
    "TransportAgent",
    "TrippyADKWorkflow",
    "TrippyAgent",
    "TrippyCrew",
    "adk_workflow_service",
]

_LAZY_ATTRS = {"TrippyADKWorkflow", "adk_workflow_service"}


def __getattr__(name: str):
    """Lazily expose ADK workflow exports without breaking startup."""
    if name in _LAZY_ATTRS:
        try:
            from . import adk_adapter

            return getattr(adk_adapter, name)
        except ImportError:
            raise AttributeError(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")