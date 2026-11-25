"""
TRIPPY Backend — Sequential Multi-Agent Stages Router

Provides independent, step-by-step API endpoints for each of the 5 specialist agents:
1. Destination Agent  (/api/trips/stages/destination)
2. Transport Agent    (/api/trips/stages/transport)
3. Stay & Activity    (/api/trips/stages/stay-activity)
4. Budget Agent       (/api/trips/stages/budget)
5. Itinerary Agent    (/api/trips/stages/itinerary - finalize & persist)
"""

from datetime import date
from typing import Any, List, Optional
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import (
    BudgetAgent,
    DestinationAgent,
    ItineraryAgent,
    StayActivityAgent,
    TransportAgent,
)
from app.integrations import route_service, weather_service
from app.rag import rag_service
from app.schemas.agent_outputs import (
    BudgetAgentOutput,
    DestinationAgentOutput,
    StayActivityAgentOutput,
    TransportAgentOutput,
)
from app.schemas.trip import (
    BudgetBreakdown,
    RouteEstimate,
    TransportMode,
    TravelStyle,
    TripPreferences,
    TripResult,
    WeatherForecast,
)
from app.services import location_verifier
from app.storage import trip_repository
from app.tools.budget_tools import calculate_itemized_budget

router = APIRouter(prefix="/trips/stages", tags=["stages"])

destination_agent = DestinationAgent()
transport_agent = TransportAgent()
stay_activity_agent = StayActivityAgent()
budget_agent = BudgetAgent()
itinerary_agent = ItineraryAgent()


# ─── Stage 1: Destination Agent ──────────────────────────────────────────

class DestinationStageRequest(BaseModel):
    origin: str = Field(..., examples=["New Delhi, India"])
    destinations: Optional[List[str]] = Field(default=None, examples=[["Kyoto, Japan"]])
    start_date: date
    end_date: date
    budget_max: Optional[float] = None
    currency: str = "USD"
    travel_style: TravelStyle = TravelStyle.cultural
    interests: List[str] = Field(default_factory=list)


@router.post("/destination", response_model=DestinationAgentOutput)
async def stage_destination(req: DestinationStageRequest) -> DestinationAgentOutput:
    """Stage 1: Evaluates preferences and returns ranked destination candidates."""
    if req.end_date <= req.start_date:
        raise HTTPException(status_code=422, detail="Trip end date must be after start date.")

    # Validate origin location
    check_orig = await location_verifier.verify_location(req.origin)
    if not check_orig.is_valid:
        raise HTTPException(
            status_code=422,
            detail=check_orig.error_message or f"Invalid origin: '{req.origin}'.",
        )

    # Validate explicit destination if specified
    if req.destinations:
        for dest in req.destinations:
            check_dest = await location_verifier.verify_location(dest)
            if not check_dest.is_valid:
                raise HTTPException(
                    status_code=422,
                    detail=check_dest.error_message or f"Invalid destination: '{dest}'.",
                )

    pref = TripPreferences(
        origin=req.origin,
        destinations=req.destinations,
        start_date=req.start_date,
        end_date=req.end_date,
        budget_max=req.budget_max,
        currency=req.currency,
        travel_style=req.travel_style,
        interests=req.interests,
    )

    # RAG pre-flight retrieval
    pref_query = f"{req.travel_style.value} " + " ".join(req.interests)
    dest_passages = []
    try:
        dest_passages = rag_service.retrieve(query=pref_query, top_k=3)
    except Exception:
        dest_passages = []

    return await destination_agent.run(pref, rag_passages=dest_passages)


# ─── Stage 2: Transport Agent ────────────────────────────────────────────

class TransportStageRequest(BaseModel):
    origin: str
    destination: str
    start_date: date
    end_date: date
    travelers: int = Field(default=1, ge=1)
    preferred_transport: TransportMode = TransportMode.mixed
    travel_style: TravelStyle = TravelStyle.cultural
    currency: str = "USD"
    refinement_level: int = 0


class TransportStageResponse(BaseModel):
    transport: TransportAgentOutput
    route_estimate: Optional[RouteEstimate] = None


@router.post("/transport", response_model=TransportStageResponse)
async def stage_transport(req: TransportStageRequest) -> TransportStageResponse:
    """Stage 2: Calculates transit routing, flight/train corridors, and pricing."""
    pref = TripPreferences(
        origin=req.origin,
        destinations=[req.destination],
        start_date=req.start_date,
        end_date=req.end_date,
        travelers=req.travelers,
        preferred_transport=req.preferred_transport,
        travel_style=req.travel_style,
        currency=req.currency,
    )

    # Fetch live/geodesic route estimate
    route_res = None
    try:
        route_res = await route_service.get_route(
            origin=req.origin,
            destination=req.destination,
            mode=req.preferred_transport.value,
        )
    except Exception:
        route_res = None

    transport_output = await transport_agent.run(
        preferences=pref,
        destination=req.destination,
        refinement_level=req.refinement_level,
        route_info=route_res,
    )

    return TransportStageResponse(
        transport=transport_output,
        route_estimate=route_res,
    )


# ─── Stage 3: Stay & Activity Agent ──────────────────────────────────────

class StayActivityStageRequest(BaseModel):
    destination: str
    start_date: date
    end_date: date
    travelers: int = Field(default=1, ge=1)
    travel_style: TravelStyle = TravelStyle.cultural
    interests: List[str] = Field(default_factory=list)
    currency: str = "USD"
    refinement_level: int = 0


class StayActivityStageResponse(BaseModel):
    stay_activity: StayActivityAgentOutput
    weather: Optional[WeatherForecast] = None
    rag_sources: List[str] = Field(default_factory=list)
    destination_guidance: List[str] = Field(default_factory=list)


@router.post("/stay-activity", response_model=StayActivityStageResponse)
async def stage_stay_activity(req: StayActivityStageRequest) -> StayActivityStageResponse:
    """Stage 3: Curates hotel lodging, local landmarks, dining allowance, and weather."""
    pref = TripPreferences(
        origin="Unknown",
        destinations=[req.destination],
        start_date=req.start_date,
        end_date=req.end_date,
        travelers=req.travelers,
        travel_style=req.travel_style,
        interests=req.interests,
        currency=req.currency,
    )

    # Fetch live/fallback weather
    weather_res = None
    try:
        weather_res = await weather_service.get_forecast(
            destination=req.destination,
            start_date=req.start_date,
            end_date=req.end_date,
        )
    except Exception:
        weather_res = None

    # Fetch destination RAG guidebooks
    stay_passages = []
    city_prefix = req.destination.split(",")[0].strip().lower()
    try:
        stay_query = f"{city_prefix} lodging hotels activities dining etiquette"
        stay_passages = rag_service.retrieve(query=stay_query, destination=req.destination, top_k=4)
    except Exception:
        stay_passages = []

    matching = [
        p for p in stay_passages
        if p.destination and (city_prefix in p.destination.lower() or p.destination.lower() in req.destination.lower())
    ]
    rag_sources = list(dict.fromkeys(p.source for p in matching if p.source))
    destination_guidance = [
        f"[{p.section}] {p.text.strip()} (Source: {p.source})"
        for p in matching[:5]
    ]

    stay_output = await stay_activity_agent.run(
        preferences=pref,
        destination=req.destination,
        refinement_level=req.refinement_level,
        rag_passages=stay_passages,
    )

    return StayActivityStageResponse(
        stay_activity=stay_output,
        weather=weather_res,
        rag_sources=rag_sources,
        destination_guidance=destination_guidance,
    )


# ─── Stage 4: Budget Agent ───────────────────────────────────────────────

class BudgetStageRequest(BaseModel):
    transport_cost: float = Field(..., ge=0.0)
    accommodation_cost: float = Field(..., ge=0.0)
    activities_cost: float = Field(..., ge=0.0)
    food_cost: float = Field(..., ge=0.0)
    budget_max: Optional[float] = None
    currency: str = "USD"


@router.post("/budget", response_model=BudgetAgentOutput)
async def stage_budget(req: BudgetStageRequest) -> BudgetAgentOutput:
    """Stage 4: Audits itemized expenses with deterministic Python math and contingency."""
    breakdown = calculate_itemized_budget(
        transport_cost=req.transport_cost,
        accommodation_cost=req.accommodation_cost,
        activities_cost=req.activities_cost,
        food_cost=req.food_cost,
        currency=req.currency,
    )

    return await budget_agent.run(
        breakdown=breakdown,
        budget_max=req.budget_max,
        currency=req.currency,
    )


# ─── Stage 5: Itinerary Agent & Finalize ─────────────────────────────────

class ItineraryStageRequest(BaseModel):
    preferences: TripPreferences
    destination: str
    transport: TransportAgentOutput
    stay_activity: StayActivityAgentOutput
    budget: BudgetAgentOutput
    weather: Optional[WeatherForecast] = None
    route_estimate: Optional[RouteEstimate] = None
    rag_sources: List[str] = Field(default_factory=list)
    destination_guidance: List[str] = Field(default_factory=list)


@router.post("/itinerary", response_model=TripResult)
async def stage_itinerary(req: ItineraryStageRequest) -> TripResult:
    """Stage 5: Synthesizes final day-by-day plan with AI narrative and persists to storage."""
    budget_warning: Optional[str] = None
    if not req.budget.is_within_budget and req.preferences.budget_max:
        curr_sym = "₹" if req.preferences.currency.upper() == "INR" else ("€" if req.preferences.currency.upper() == "EUR" else ("£" if req.preferences.currency.upper() == "GBP" else "$"))
        budget_warning = (
            f"Budget Notice: Total {curr_sym}{req.budget.breakdown.total:.2f} {req.preferences.currency} "
            f"exceeds limit of {curr_sym}{req.preferences.budget_max:.2f} by {curr_sym}{req.budget.overflow_amount:.2f}."
        )

    itinerary_output = await itinerary_agent.run(
        preferences=req.preferences,
        destination=req.destination,
        transport=req.transport,
        stay_activity=req.stay_activity,
        budget=req.budget,
        budget_warning=budget_warning,
        weather=req.weather,
        route=req.route_estimate,
    )

    trip_id = f"trip_{uuid.uuid4().hex[:10]}"
    all_destinations = [req.destination]
    if req.preferences.destinations:
        all_destinations = req.preferences.destinations

    result = TripResult(
        trip_id=trip_id,
        preferences=req.preferences,
        destinations=all_destinations,
        currency=req.preferences.currency,
        itinerary=itinerary_output.days,
        budget=req.budget.breakdown,
        summary=itinerary_output.summary,
        warnings=itinerary_output.warnings,
        weather=req.weather,
        route_estimate=req.route_estimate,
        rag_sources=req.rag_sources,
        destination_guidance=req.destination_guidance,
    )

    try:
        trip_repository.save(result)
    except Exception:
        pass

    return result
