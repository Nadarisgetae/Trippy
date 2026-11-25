"""
TRIPPY Backend — Stay & Activity Agent

Agent 3: Stay & Activity Specialist.
Recommends accommodation categories, activities and food.
"""

from typing import Optional

from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import StayActivityAgentOutput
from app.schemas.trip import TripPreferences
from app.services.llm_provider import llm_service
from app.tools.stay_activity_tools import recommend_stays_and_activities


class StayActivityAgent(TrippyAgent):
    """Stay & Activity Specialist recommending accommodations, activities, and dining."""

    def __init__(self):
        super().__init__(
            role="Stay & Activity Specialist",
            goal="Recommend accommodation categories, curated daily activities, and food budgets matching travel style and tier.",
            backstory=(
                "Boutique hospitality director and local experience curator. "
                "Known for selecting character-rich hotels and authentic cultural, culinary, and outdoor activities."
            ),
            tools=[recommend_stays_and_activities],
        )

    async def run(
        self,
        preferences: TripPreferences,
        destination: str,
        refinement_level: int = 0,
        rag_passages: Optional[list] = None,
    ) -> StayActivityAgentOutput:
        """
        Recommends stays, activities, and food budget with optional RAG context.
        refinement_level: 0 (default), 1 (midscale saver), 2 (deep budget).
        """
        duration_days = max(1, (preferences.end_date - preferences.start_date).days)

        # 1. Fetch live real-world landmarks and currency exchange rate
        landmarks_list = []
        live_rate = None
        try:
            from app.integrations.places import places_service
            place_info = await places_service.get_destination_info(destination)
            if place_info and place_info.landmarks:
                landmarks_list = place_info.landmarks
        except Exception:
            pass

        try:
            from app.integrations.forex import forex_service
            live_rate = await forex_service.get_multiplier_from_usd(preferences.currency)
        except Exception:
            pass

        deterministic_output = recommend_stays_and_activities(
            destination=destination,
            travel_style=preferences.travel_style,
            start_date=preferences.start_date,
            duration_days=duration_days,
            travelers=preferences.travelers,
            interests=preferences.interests,
            refinement_level=refinement_level,
            currency=preferences.currency,
            live_forex_rate=live_rate,
            landmarks=landmarks_list,
        )

        # Incorporate RAG guidebook tips
        if rag_passages:
            for passage in rag_passages[:2]:
                deterministic_output.food_highlights.append(
                    f"Guidebook tip: {passage.section} — {passage.text[:90]}… [Source: {passage.source}]"
                )
                if deterministic_output.activities:
                    # Enrich first activity description with guidebook reference
                    deterministic_output.activities[0].description += f" (Curated via {passage.source})"

        # 2. If AI is available, generate structured stay & activity recommendations
        if llm_service.is_available():
            try:
                places_ctx = ""
                if landmarks_list:
                    lm_summary = "\n".join(
                        f"- {getattr(l, 'name', str(l))}: {getattr(l, 'description', '')}"
                        for l in landmarks_list[:6]
                    )
                    places_ctx = f"Verified local sights and landmarks in {destination}:\n{lm_summary}\n"

                prompt = (
                    f"Destination: '{destination}'. Duration: {duration_days} days. Travelers: {preferences.travelers}.\n"
                    f"Travel style: {preferences.travel_style.value}. Interests: {', '.join(preferences.interests) if preferences.interests else 'general'}.\n"
                    f"Currency: {preferences.currency}.\n"
                    f"{places_ctx}"
                    f"CRITICAL REQUIREMENTS:\n"
                    f"1. For activities, you MUST provide ACTUAL, SPECIFIC REAL NAMES of famous monuments, heritage sights, temples, lakes, museums, or culinary quarters in '{destination}' "
                    f"(e.g., for Bhopal: 'Taj-ul-Masajid', 'Upper Lake (Bhojtal) & Van Vihar', 'Sanchi Stupa', 'Bhimbetka Rock Shelters', 'Madhya Pradesh Tribal Museum', NOT generic names like 'Bhopal Heritage Walk').\n"
                    f"2. Under each activity, write an authentic 2-3 sentence description detailing what it is, its historical era or founder, architectural significance, and experience.\n"
                    f"3. Provide realistic cost_estimate (0 for free monuments/lakes/gardens, small admission fees otherwise).\n"
                    f"4. Provide verified source_url (e.g., https://en.wikipedia.org/wiki/...) and source_label.\n"
                    f"5. Provide real hotel options in '{destination}' across luxury, boutique, midscale, and budget categories with realistic night rates in {preferences.currency} and booking links.\n"
                    f"Provide at least {min(duration_days, 6)} distinct real activities."
                )
                system = (
                    f"You are the {self.role}. {self.backstory}. "
                    f"Always provide real, specific names of tourist attractions, detailed explanations of what they are, and authentic hotels."
                )
                ai_res = await llm_service.generate_structured(prompt, system, StayActivityAgentOutput)
                if ai_res and ai_res.activities and len(ai_res.activities) >= 2:
                    if not any("historic city center & heritage walk" in a.name.lower() for a in ai_res.activities):
                        if not ai_res.hotel_options and deterministic_output.hotel_options:
                            ai_res.hotel_options = deterministic_output.hotel_options
                        if not ai_res.accommodation_name and deterministic_output.accommodation_name:
                            ai_res.accommodation_name = deterministic_output.accommodation_name
                            ai_res.accommodation_category = deterministic_output.accommodation_category
                            ai_res.cost_per_night = deterministic_output.cost_per_night
                            ai_res.total_stay_cost = deterministic_output.total_stay_cost
                        return ai_res
            except Exception:
                pass

        return deterministic_output
