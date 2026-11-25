"""
TRIPPY Backend — Transport Agent

Agent 2: Transport Specialist.
Estimates transport cost, routes, durations, and cost-reduction alternatives.
"""

from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import TransportAgentOutput
from app.schemas.trip import TripPreferences
from app.services.llm_provider import llm_service
from app.tools.transport_tools import estimate_transport


class TransportAgent(TrippyAgent):
    """Transport Specialist responsible for estimating transit legs and costs."""

    def __init__(self):
        super().__init__(
            role="Transport Specialist",
            goal="Estimate transport cost and duration using supported data, routing modes, and realistic options.",
            backstory=(
                "Global transit logistics and route planning specialist. Expert at comparing flights, "
                "high-speed trains, scenic rail, and road connections to balance comfort, travel time, and cost."
            ),
            tools=[estimate_transport],
        )

    async def run(
        self,
        preferences: TripPreferences,
        destination: str,
        refinement_level: int = 0,
        route_info: Optional[Any] = None,
    ) -> TransportAgentOutput:
        """
        Calculates transport estimates between origin and destination.
        refinement_level: 0 (default), 1 (economy saver), 2 (deep budget).
        """
        if route_info is None:
            try:
                from app.integrations.maps import route_service
                route_info = await route_service.get_route(
                    origin=preferences.origin,
                    destination=destination,
                    mode=preferences.preferred_transport.value,
                )
            except Exception:
                pass

        live_rate = None
        try:
            from app.integrations.forex import forex_service
            live_rate = await forex_service.get_multiplier_from_usd(preferences.currency)
        except Exception:
            pass

        # Look up live Google Search / outstation tariff quote
        search_quote = None
        try:
            from app.integrations.search import search_pricing_service
            search_quote = await search_pricing_service.lookup_transit_fare(
                origin=preferences.origin,
                destination=destination,
                mode=preferences.preferred_transport,
                travelers=preferences.travelers,
                distance_km=route_info.distance_km if route_info else None,
                currency=preferences.currency,
                forex_rate=live_rate or 1.0,
            )
        except Exception:
            search_quote = None

        deterministic_res = estimate_transport(
            origin=preferences.origin,
            destination=destination,
            preferred_mode=preferences.preferred_transport,
            travelers=preferences.travelers,
            travel_style=preferences.travel_style,
            refinement_level=refinement_level,
            currency=preferences.currency,
            live_forex_rate=live_rate,
            distance_km=route_info.distance_km if route_info else None,
            route_duration_hours=route_info.duration_hours if route_info else None,
            live_fare_quote=search_quote,
        )

        if llm_service.is_available():
            try:
                dist_info = f"Route distance: ~{route_info.distance_km:.0f} km, estimated duration: {route_info.duration_hours:.1f}h." if route_info else ""
                veh_info = deterministic_res.legs[0].notes if deterministic_res.legs else ""
                prompt = (
                    f"Traveler departing from '{preferences.origin}' to '{destination}' for {preferences.travelers} traveler(s).\n"
                    f"{dist_info} Preferred mode: {preferences.preferred_transport.value}. Style: {preferences.travel_style.value}. Currency: {preferences.currency}.\n"
                    f"Verified pricing model: {veh_info}.\n"
                    f"Provide authentic real-world transit legs. You must return exactly 2 primary legs: "
                    f"Leg 1 is outbound from '{preferences.origin}' to '{destination}', and Leg 2 is return from '{destination}' to '{preferences.origin}'. "
                    f"(If connecting flights or multi-step transfers are involved, specify details in the notes field while keeping exactly 2 legs: outbound and return).\n"
                    f"Realistic baseline round-trip cost for all {preferences.travelers} travelers is ~{deterministic_res.total_cost} {preferences.currency}."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, TransportAgentOutput)
                if ai_res and ai_res.legs and ai_res.total_cost > 0:
                    if not ai_res.alternatives:
                        ai_res.alternatives = deterministic_res.alternatives
                    # Preserve verified vehicle notes if AI returned generic notes
                    if deterministic_res.legs and "[Source:" in deterministic_res.legs[0].notes:
                        for l in ai_res.legs:
                            if "[Source:" not in (l.notes or ""):
                                l.notes = deterministic_res.legs[0].notes
                    if len(ai_res.legs) == 2:
                        return ai_res
                    elif len(ai_res.legs) > 2:
                        # Consolidate connecting sub-legs into exactly 2 primary legs (outbound & return)
                        first_leg = ai_res.legs[0]
                        last_leg = ai_res.legs[-1]
                        first_leg.origin = preferences.origin
                        first_leg.destination = destination
                        last_leg.origin = destination
                        last_leg.destination = preferences.origin
                        half_cost = round(ai_res.total_cost / 2.0, 2)
                        first_leg.cost_estimate = half_cost
                        last_leg.cost_estimate = half_cost
                        ai_res.legs = [first_leg, last_leg]
                        return ai_res
            except Exception:
                pass

        return deterministic_res
