"""
TRIPPY Backend — Destination Tools

Reusable tools for destination knowledge lookup, ranking, and matchmaking
based on traveler style, interests, duration, and budget.
"""

from typing import Any, Dict, List, Optional
from app.schemas.agent_outputs import DestinationCandidate
from app.schemas.trip import TravelStyle

# Approximate conversion rates to USD for heuristic budget evaluation
CURRENCY_MULTIPLIERS: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 86.5,
    "JPY": 155.0,
    "CAD": 1.38,
    "AUD": 1.52,
    "CHF": 0.90,
    "SGD": 1.34,
    "AED": 3.67,
    "THB": 36.5,
}


DESTINATION_CATALOG: List[Dict[str, Any]] = [
    # ── India & South Asia Regional Getaways ──
    {
        "name": "Agra, India",
        "country": "India",
        "styles": [TravelStyle.cultural, TravelStyle.romantic, TravelStyle.family, TravelStyle.budget],
        "interests": ["history", "architecture", "food", "photography", "temples"],
        "cost_tier": "budget",
        "avg_daily_cost": 35.0,
        "recommended_days": 2,
        "highlights": ["Taj Mahal at Sunrise", "Agra Fort", "Fatehpur Sikri", "Sadar Bazaar Petha Walk"],
    },
    {
        "name": "Haridwar & Rishikesh, India",
        "country": "India",
        "styles": [TravelStyle.cultural, TravelStyle.adventure, TravelStyle.relaxation, TravelStyle.budget],
        "interests": ["temples", "nature", "adventure", "wellness", "culture", "history"],
        "cost_tier": "budget",
        "avg_daily_cost": 30.0,
        "recommended_days": 3,
        "highlights": ["Har Ki Pauri Evening Ganga Aarti", "Rishikesh White Water Rafting", "Beatles Ashram & Yoga", "Triveni Ghat"],
    },
    {
        "name": "Mathura & Vrindavan, India",
        "country": "India",
        "styles": [TravelStyle.cultural, TravelStyle.budget],
        "interests": ["temples", "history", "food", "culture"],
        "cost_tier": "budget",
        "avg_daily_cost": 25.0,
        "recommended_days": 2,
        "highlights": ["Shri Krishna Janmabhoomi", "Banke Bihari Temple", "Prem Mandir Light Show", "Vrindavan Parikrama"],
    },
    {
        "name": "Jaipur, India",
        "country": "India",
        "styles": [TravelStyle.cultural, TravelStyle.family, TravelStyle.romantic],
        "interests": ["history", "architecture", "food", "photography", "art"],
        "cost_tier": "budget",
        "avg_daily_cost": 40.0,
        "recommended_days": 3,
        "highlights": ["Amber Fort & Sheesh Mahal", "Hawa Mahal & City Palace", "Nahargarh Fort Sunset", "Johari Bazaar Artisans"],
    },
    {
        "name": "Dehradun & Mussoorie, India",
        "country": "India",
        "styles": [TravelStyle.relaxation, TravelStyle.adventure, TravelStyle.romantic],
        "interests": ["nature", "mountains", "food", "hiking", "photography"],
        "cost_tier": "midscale",
        "avg_daily_cost": 45.0,
        "recommended_days": 4,
        "highlights": ["Robber's Cave (Guchhupani)", "Mussoorie Mall Road & Gun Hill", "Kempty Falls", "George Everest Peak"],
    },
    {
        "name": "Kasol & Parvati Valley, India",
        "country": "India",
        "styles": [TravelStyle.adventure, TravelStyle.relaxation, TravelStyle.budget],
        "interests": ["mountains", "trekking", "nature", "food", "cafes"],
        "cost_tier": "budget",
        "avg_daily_cost": 30.0,
        "recommended_days": 4,
        "highlights": ["Chalal Riverside Trail", "Manikaran Sahib Thermal Springs", "Tosh Himalayan Panorama", "Kheerganga Meadow Trek"],
    },
    {
        "name": "Varanasi, India",
        "country": "India",
        "styles": [TravelStyle.cultural, TravelStyle.budget],
        "interests": ["temples", "history", "culture", "photography", "food"],
        "cost_tier": "budget",
        "avg_daily_cost": 30.0,
        "recommended_days": 3,
        "highlights": ["Dashashwamedh Ghat Evening Aarti", "Sunrise Boat Ride on Ganges", "Kashi Vishwanath Corridor", "Sarnath Buddhist Stupa"],
    },
    # ── International Catalog Destinations ──
    {
        "name": "Kyoto, Japan",
        "country": "Japan",
        "styles": [TravelStyle.cultural, TravelStyle.relaxation, TravelStyle.romantic],
        "interests": ["history", "temples", "food", "nature", "photography", "architecture"],
        "cost_tier": "midscale",  # budget, midscale, luxury
        "avg_daily_cost": 160.0,
        "recommended_days": 5,
        "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Gion District", "Kinkaku-ji"],
    },
    {
        "name": "Rome, Italy",
        "country": "Italy",
        "styles": [TravelStyle.cultural, TravelStyle.romantic, TravelStyle.family],
        "interests": ["history", "food", "art", "architecture", "photography"],
        "cost_tier": "midscale",
        "avg_daily_cost": 175.0,
        "recommended_days": 4,
        "highlights": ["Colosseum & Roman Forum", "Vatican Museums", "Trevi Fountain", "Trastevere Food Walk"],
    },
    {
        "name": "Bali, Indonesia",
        "country": "Indonesia",
        "styles": [TravelStyle.relaxation, TravelStyle.adventure, TravelStyle.budget, TravelStyle.romantic],
        "interests": ["beaches", "wellness", "nature", "surfing", "culture", "food"],
        "cost_tier": "budget",
        "avg_daily_cost": 85.0,
        "recommended_days": 7,
        "highlights": ["Ubud Rice Terraces", "Uluwatu Temple Sunset", "Mount Batur Sunrise Trek", "Seminyak Beach"],
    },
    {
        "name": "Swiss Alps (Interlaken), Switzerland",
        "country": "Switzerland",
        "styles": [TravelStyle.adventure, TravelStyle.luxury, TravelStyle.romantic],
        "interests": ["hiking", "mountains", "nature", "photography", "adventure sports"],
        "cost_tier": "luxury",
        "avg_daily_cost": 290.0,
        "recommended_days": 5,
        "highlights": ["Jungfraujoch Top of Europe", "Lake Brienz Cruise", "Lauterbrunnen Valley", "Harder Kulm"],
    },
    {
        "name": "Barcelona, Spain",
        "country": "Spain",
        "styles": [TravelStyle.cultural, TravelStyle.budget, TravelStyle.family],
        "interests": ["architecture", "beaches", "food", "art", "nightlife"],
        "cost_tier": "midscale",
        "avg_daily_cost": 150.0,
        "recommended_days": 5,
        "highlights": ["Sagrada Família", "Park Güell", "Gothic Quarter", "Barceloneta Beach"],
    },
    {
        "name": "Costa Rica (Arenal & Manuel Antonio)",
        "country": "Costa Rica",
        "styles": [TravelStyle.adventure, TravelStyle.family, TravelStyle.relaxation],
        "interests": ["wildlife", "rainforest", "nature", "beaches", "ziplining"],
        "cost_tier": "midscale",
        "avg_daily_cost": 140.0,
        "recommended_days": 6,
        "highlights": ["Arenal Volcano National Park", "Manuel Antonio Beaches", "Monteverde Cloud Forest", "Hot Springs"],
    },
    {
        "name": "Paris, France",
        "country": "France",
        "styles": [TravelStyle.romantic, TravelStyle.cultural, TravelStyle.luxury],
        "interests": ["art", "food", "fashion", "history", "architecture", "museums"],
        "cost_tier": "luxury",
        "avg_daily_cost": 240.0,
        "recommended_days": 5,
        "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Seine River Cruise"],
    },
    {
        "name": "Bangkok & Chiang Mai, Thailand",
        "country": "Thailand",
        "styles": [TravelStyle.budget, TravelStyle.cultural, TravelStyle.adventure],
        "interests": ["street food", "temples", "night markets", "culture", "nature"],
        "cost_tier": "budget",
        "avg_daily_cost": 70.0,
        "recommended_days": 7,
        "highlights": ["Grand Palace Bangkok", "Chiang Mai Old City", "Elephant Sanctuary", "Chatuchak Market"],
    },
]


def rank_destination_candidates(
    origin: str,
    requested_destinations: Optional[List[str]],
    travel_style: TravelStyle,
    duration_days: int,
    budget_max: Optional[float],
    interests: List[str],
    currency: str = "USD",
) -> List[DestinationCandidate]:
    """
    Ranks destination candidates using traveler style, interest overlap,
    budget viability, and trip duration.
    """
    candidates: List[DestinationCandidate] = []
    requested_names_lower = {d.lower() for d in (requested_destinations or [])}

    # 1. If the user specified specific destinations, prioritize them at top rank
    if requested_destinations and len(requested_destinations) > 0:
        for idx, dest_name in enumerate(requested_destinations, start=1):
            matching_catalog = next(
                (d for d in DESTINATION_CATALOG if dest_name.lower() in d["name"].lower() or d["name"].lower() in dest_name.lower()),
                None,
            )
            country = matching_catalog["country"] if matching_catalog else "International"
            highlights = matching_catalog["highlights"] if matching_catalog else ["City center", "Local landmarks", "Historic sites"]
            score = 95.0 - (idx - 1) * 5.0

            candidates.append(
                DestinationCandidate(
                    name=dest_name,
                    country=country,
                    rank=idx,
                    match_score=score,
                    highlights=highlights,
                    recommended_days=duration_days,
                    why_matched=f"Explicitly requested by traveler from {origin}.",
                )
            )

    # 2. Score catalog destinations for alternatives
    scored = []
    user_interests_lower = {i.lower() for i in interests}

    # Detect geographic country context from origin or requested destinations
    all_context = f"{origin} {' '.join(requested_destinations or [])}".lower()
    target_country = None
    if any(k in all_context for k in ["india", "delhi", "meerut", "merrut", "ghaziabad", "noida", "gurgaon", "gurugram", "agra", "jaipur"]):
        target_country = "India"
    elif any(k in all_context for k in ["japan", "tokyo", "kyoto", "osaka"]):
        target_country = "Japan"
    elif any(k in all_context for k in ["italy", "rome", "milan", "florence"]):
        target_country = "Italy"
    elif any(k in all_context for k in ["france", "paris", "nice"]):
        target_country = "France"
    elif any(k in all_context for k in ["spain", "barcelona", "madrid"]):
        target_country = "Spain"
    elif any(k in all_context for k in ["indonesia", "bali", "jakarta"]):
        target_country = "Indonesia"
    elif any(k in all_context for k in ["switzerland", "swiss", "interlaken"]):
        target_country = "Switzerland"

    for item in DESTINATION_CATALOG:
        # Avoid duplicating requested destinations
        if any(r in item["name"].lower() or item["name"].lower() in r for r in requested_names_lower):
            continue

        score = 50.0  # baseline

        # Geographic proximity boost: favor destinations in the same country/region
        if target_country:
            if item["country"].lower() == target_country.lower():
                score += 35.0
            else:
                score -= 35.0

        # Travel style match (+25 points)
        if travel_style in item["styles"]:
            score += 25.0

        # Interests overlap (up to +20 points)
        item_interests = {i.lower() for i in item["interests"]}
        overlap = len(user_interests_lower.intersection(item_interests))
        score += min(overlap * 6.0, 20.0)

        # Budget suitability (+5 points if budget matches cost tier)
        if budget_max is not None and duration_days > 0:
            est_total = item["avg_daily_cost"] * duration_days + 400.0  # rough baseline in USD
            # Convert budget_max to USD for comparison (budget_max is in user's currency)
            rate = CURRENCY_MULTIPLIERS.get(currency.upper(), 1.0)
            budget_in_usd = budget_max / rate
            if est_total <= budget_in_usd:
                score += 5.0
            else:
                score -= 10.0  # slight penalty for likely over-budget

        score = max(10.0, min(99.0, score))
        scored.append((score, item))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Fill up to 4 candidates with top alternative recommendations
    needed = max(0, 4 - len(candidates))
    for item_score, item in scored[:needed]:
        rank = len(candidates) + 1
        candidates.append(
            DestinationCandidate(
                name=item["name"],
                country=item["country"],
                rank=rank,
                match_score=round(item_score, 1),
                highlights=item["highlights"],
                recommended_days=min(duration_days, item["recommended_days"]),
                why_matched=f"Curated recommendation for {travel_style.value} style with high alignment on {', '.join(item['interests'][:3])}.",
            )
        )

    return candidates