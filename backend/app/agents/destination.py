"""
TRIPPY Backend — Destination Agent

Agent 1: Destination Specialist.
Ranks destinations using preferences, duration, budget, and travel style.
"""

from typing import Optional
from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import DestinationAgentOutput
from app.schemas.trip import TripPreferences
from app.services.llm_provider import llm_service
from app.tools.destination_tools import rank_destination_candidates


class DestinationAgent(TrippyAgent):
    """Destination Specialist that selects and ranks travel candidates."""

    def __init__(self):
        super().__init__(
            role="Destination Specialist",
            goal="Analyze traveler preferences, duration, style, and budget to select and rank optimal destination candidates.",
            backstory=(
                "Senior travel curator with 15+ years of global travel matchmaking experience. "
                "Master at uncovering destinations that balance personal interests, optimal timing, and budget constraints."
            ),
            tools=[rank_destination_candidates],
        )

    async def run(
        self,
        preferences: TripPreferences,
        rag_passages: Optional[list] = None,
    ) -> DestinationAgentOutput:
        """
        Executes destination matchmaking workflow with optional RAG passage context.
        """
        duration_days = max(1, (preferences.end_date - preferences.start_date).days)

        # 1. Deterministic baseline candidates via tool
        candidates = rank_destination_candidates(
            origin=preferences.origin,
            requested_destinations=preferences.destinations,
            travel_style=preferences.travel_style,
            duration_days=duration_days,
            budget_max=preferences.budget_max,
            interests=preferences.interests,
            currency=preferences.currency,
        )

        selected = candidates[0].name if candidates else (preferences.destinations[0] if preferences.destinations else "Kyoto, Japan")
        rationale = (
            f"Selected {selected} based on top match score for {preferences.travel_style.value} style, "
            f"aligning with {', '.join(preferences.interests) if preferences.interests else 'curated highlights'}."
        )

        # Incorporate real-world place knowledge via Wikipedia Places integration
        real_info = None
        try:
            from app.integrations.places import places_service
            real_info = await places_service.get_destination_info(selected)
            if real_info and real_info.summary and candidates:
                candidates[0].why_matched += f" Grounded in verified geographical data: {real_info.summary[:120]}…"
        except Exception:
            pass

        # Incorporate RAG guidebook insights if available
        if rag_passages:
            city_prefix = selected.split(",")[0].strip().lower()
            matching_passage = next(
                (
                    p for p in rag_passages
                    if p.destination and (
                        city_prefix in p.destination.lower()
                        or p.destination.lower() in selected.lower()
                    )
                ),
                None,
            )
            if matching_passage:
                rationale += f" Guidance supported by {matching_passage.source} ({matching_passage.section})."
                if candidates:
                    candidates[0].why_matched += f" [Source: {matching_passage.source}]"
            elif real_info and real_info.summary:
                rationale += " Grounded in verified regional geography and attractions."
                if candidates and "[Source:" not in candidates[0].why_matched:
                    candidates[0].why_matched += " [Source: Verified Geographical Database]"

        deterministic_output = DestinationAgentOutput(
            selected_destination=selected,
            candidates=candidates,
            rationale=rationale,
        )

        # 2. If AI is available, refine destination candidate matchmaking and geographical alternatives
        if llm_service.is_available():
            try:
                user_fixed = ""
                if preferences.destinations:
                    user_fixed = (
                        f"The user has explicitly chosen primary destination: '{selected}'.\n"
                        f"Candidate 0 (Rank 1, 95% Match) MUST be '{selected}'.\n"
                        f"Candidates 1, 2, and 3 MUST be real, authentic alternative destinations GEOGRAPHICALLY RELEVANT to the trip "
                        f"(e.g., if traveling to Meerut or New Delhi, recommend nearby regional Indian getaways such as Haridwar/Rishikesh, Agra, Mathura/Vrindavan, or Jaipur, NOT different continents like Kyoto, Rome, or Paris!).\n"
                    )

                live_wiki_ctx = ""
                if real_info and real_info.summary:
                    lm_names = ", ".join(l.name for l in real_info.landmarks[:5])
                    live_wiki_ctx = f"Verified geographical summary: {real_info.summary[:300]}\nKey landmarks: {lm_names}\n"

                prompt = (
                    f"{user_fixed}"
                    f"Traveler from {preferences.origin} planning a {duration_days}-day {preferences.travel_style.value} trip.\n"
                    f"Interests: {preferences.interests}.\n"
                    f"Budget: {preferences.budget_max} {preferences.currency}.\n"
                    f"Top candidate: {selected}.\n"
                    f"{live_wiki_ctx}"
                    f"Provide exactly 4 ranked candidates with realistic highlights, why_matched explanations, and match scores. Ensure alternative candidates are geographically sensible."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, DestinationAgentOutput)
                if ai_res and ai_res.candidates and len(ai_res.candidates) >= 2:
                    if preferences.destinations:
                        ai_res.selected_destination = selected
                        ai_res.candidates[0].name = selected
                        ai_res.candidates[0].rank = 1
                        ai_res.candidates[0].match_score = 95.0
                    return ai_res
            except Exception:
                pass

        return deterministic_output
