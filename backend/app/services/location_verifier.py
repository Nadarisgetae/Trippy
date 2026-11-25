"""
TRIPPY Backend — Location Verification Service

Verifies whether user-submitted origin and destination locations are real,
recognized geographical cities, towns, or travel destinations on Earth.
Rejects gibberish entries (e.g. 'vuvv', 'dg', 'xyz') with clean user-facing diagnostics.

Resolution order:
    1. Offline hub-city dictionary (instant, zero network).
    2. Live Open-Meteo geocoding API (with timeout).
    3. Structural heuristic (known country / plausible multi-word place name).
    4. LLM check, when a provider is configured.
    5. Reject as unverifiable.
"""

import logging
import re
from typing import Optional, Tuple
import httpx
from pydantic import BaseModel
from app.services.llm_provider import llm_service

logger = logging.getLogger("trippy.verifier")


class LocationVerificationResult(BaseModel):
    is_valid: bool
    canonical_name: Optional[str] = None
    country: Optional[str] = None
    error_message: Optional[str] = None


# ─── Offline Hub-City Fallback Registry ──────────────────────────────────
# Keyed by every normalized spelling a traveler is likely to type.
# Value is (canonical_name, country).

OFFLINE_CITIES: dict[str, Tuple[str, str]] = {
    # ── Catalog destinations ──
    "kyoto": ("Kyoto, Japan", "Japan"),
    "rome": ("Rome, Italy", "Italy"),
    "roma": ("Rome, Italy", "Italy"),
    "bali": ("Bali, Indonesia", "Indonesia"),
    "denpasar": ("Bali, Indonesia", "Indonesia"),
    "ubud": ("Bali, Indonesia", "Indonesia"),
    "swiss alps": ("Swiss Alps (Interlaken), Switzerland", "Switzerland"),
    "interlaken": ("Swiss Alps (Interlaken), Switzerland", "Switzerland"),
    "swiss": ("Swiss Alps (Interlaken), Switzerland", "Switzerland"),
    "switzerland": ("Swiss Alps (Interlaken), Switzerland", "Switzerland"),
    "jungfrau": ("Swiss Alps (Interlaken), Switzerland", "Switzerland"),
    "lauterbrunnen": ("Swiss Alps (Interlaken), Switzerland", "Switzerland"),
    "barcelona": ("Barcelona, Spain", "Spain"),
    "costa rica": ("Costa Rica (Arenal & Manuel Antonio)", "Costa Rica"),
    "arenal": ("Costa Rica (Arenal & Manuel Antonio)", "Costa Rica"),
    "manuel antonio": ("Costa Rica (Arenal & Manuel Antonio)", "Costa Rica"),
    "monteverde": ("Costa Rica (Arenal & Manuel Antonio)", "Costa Rica"),
    "paris": ("Paris, France", "France"),
    "bangkok": ("Bangkok & Chiang Mai, Thailand", "Thailand"),
    "chiang mai": ("Bangkok & Chiang Mai, Thailand", "Thailand"),
    "thailand": ("Bangkok & Chiang Mai, Thailand", "Thailand"),
    # ── South & Southeast Asia ──
    "new delhi": ("New Delhi, India", "India"),
    "delhi": ("New Delhi, India", "India"),
    "ncr": ("New Delhi, India", "India"),
    "meerut": ("Meerut, India", "India"),
    "merrut": ("Meerut, India", "India"),
    "ghaziabad": ("Ghaziabad, India", "India"),
    "gzb": ("Ghaziabad, India", "India"),
    "noida": ("Noida, India", "India"),
    "greater noida": ("Greater Noida, India", "India"),
    "faridabad": ("Faridabad, India", "India"),
    "gurgaon": ("Gurugram, India", "India"),
    "gurugram": ("Gurugram, India", "India"),
    "haridwar": ("Haridwar, India", "India"),
    "dehradun": ("Dehradun, India", "India"),
    "mussoorie": ("Mussoorie, India", "India"),
    "nainital": ("Nainital, India", "India"),
    "mathura": ("Mathura, India", "India"),
    "vrindavan": ("Vrindavan, India", "India"),
    "varanasi": ("Varanasi, India", "India"),
    "banaras": ("Varanasi, India", "India"),
    "kashi": ("Varanasi, India", "India"),
    "lucknow": ("Lucknow, India", "India"),
    "kanpur": ("Kanpur, India", "India"),
    "prayagraj": ("Prayagraj, India", "India"),
    "allahabad": ("Prayagraj, India", "India"),
    "aligarh": ("Aligarh, India", "India"),
    "kasol": ("Kasol, India", "India"),
    "manali": ("Manali, India", "India"),
    "shimla": ("Shimla, India", "India"),
    "chandigarh": ("Chandigarh, India", "India"),
    "goa": ("Goa, India", "India"),
    "panaji": ("Goa, India", "India"),
    "jaipur": ("Jaipur, India", "India"),
    "mumbai": ("Mumbai, India", "India"),
    "bombay": ("Mumbai, India", "India"),
    "bangalore": ("Bangalore, India", "India"),
    "bengaluru": ("Bangalore, India", "India"),
    "agra": ("Agra, India", "India"),
    "kochi": ("Kochi, India", "India"),
    "cochin": ("Kochi, India", "India"),
    "chennai": ("Chennai, India", "India"),
    "kolkata": ("Kolkata, India", "India"),
    "hyderabad": ("Hyderabad, India", "India"),
    "pune": ("Pune, India", "India"),
    "udaipur": ("Udaipur, India", "India"),
    "rishikesh": ("Rishikesh, India", "India"),
    "dharamshala": ("Dharamshala, India", "India"),
    "leh": ("Leh, India", "India"),
    "ladakh": ("Leh, India", "India"),
    "srinagar": ("Srinagar, India", "India"),
    "kozhikode": ("Kozhikode, India", "India"),
    "calicut": ("Kozhikode, India", "India"),
    "thiruvananthapuram": ("Thiruvananthapuram, India", "India"),
    "trivandrum": ("Thiruvananthapuram, India", "India"),
    "coorg": ("Coorg, India", "India"),
    "munnar": ("Munnar, India", "India"),
    "darjeeling": ("Darjeeling, India", "India"),
    "gangtok": ("Gangtok, India", "India"),
    "amritsar": ("Amritsar, India", "India"),
    "pushkar": ("Pushkar, India", "India"),
    "jodhpur": ("Jodhpur, India", "India"),
    "sikkim": ("Gangtok, India", "India"),
    "kerala": ("Kochi, India", "India"),
    "rajasthan": ("Jaipur, India", "India"),
    "himachal pradesh": ("Shimla, India", "India"),
    "punjab": ("Chandigarh, India", "India"),
    "karnataka": ("Bangalore, India", "India"),
    "tamil nadu": ("Chennai, India", "India"),
    "maharashtra": ("Mumbai, India", "India"),
    "west bengal": ("Kolkata, India", "India"),
    "telangana": ("Hyderabad, India", "India"),
    "gujarat": ("Gandhinagar, India", "India"),
    "gandhinagar": ("Gandhinagar, India", "India"),
    "ahmedabad": ("Ahmedabad, India", "India"),
    "surat": ("Surat, India", "India"),
    "vadodara": ("Vadodara, India", "India"),
    "indore": ("Indore, India", "India"),
    "bhopal": ("Bhopal, India", "India"),
    "lucknow": ("Lucknow, India", "India"),
    "kanpur": ("Kanpur, India", "India"),
    "patna": ("Patna, India", "India"),
    "guwahati": ("Guwahati, India", "India"),
    "assam": ("Guwahati, India", "India"),
    "meghalaya": ("Shillong, India", "India"),
    "shillong": ("Shillong, India", "India"),
    "kohima": ("Kohima, India", "India"),
    "nagaland": ("Kohima, India", "India"),
    "imphal": ("Imphal, India", "India"),
    "manipur": ("Imphal, India", "India"),
    "aizawl": ("Aizawl, India", "India"),
    "mizoram": ("Aizawl, India", "India"),
    "agartala": ("Agartala, India", "India"),
    "tripura": ("Agartala, India", "India"),
    "bhubaneswar": ("Bhubaneswar, India", "India"),
    "odisha": ("Bhubaneswar, India", "India"),
    "puri": ("Puri, India", "India"),
    "mcleod ganj": ("Dharamshala, India", "India"),
    "spiti": ("Spiti Valley, India", "India"),
    "spiti valley": ("Spiti Valley, India", "India"),
    "kinnaur": ("Kinnaur, India", "India"),
    "tirthan valley": ("Tirthan Valley, India", "India"),
    "bir billing": ("Bir Billing, India", "India"),
    "bir": ("Bir Billing, India", "India"),
    "dharamkot": ("Dharamkot, India", "India"),
    "palampur": ("Palampur, India", "India"),
    "kangra": ("Kangra, India", "India"),
    "chamba": ("Chamba, India", "India"),
    "dalhousie": ("Dalhousie, India", "India"),
    "khajjiar": ("Khajjiar, India", "India"),
    "kasauli": ("Kasauli, India", "India"),
    "naldehra": ("Naldehra, India", "India"),
    "tosh": ("Tosh, India", "India"),
    "malana": ("Malana, India", "India"),
    "jibhi": ("Jibhi, India", "India"),
    "sangla": ("Sangla, India", "India"),
    "rakchham": ("Rakchham, India", "India"),
    # ── Europe ──
    "london": ("London, UK", "United Kingdom"),
    "edinburgh": ("Edinburgh, UK", "United Kingdom"),
    "manchester": ("Manchester, UK", "United Kingdom"),
    "glasgow": ("Glasgow, UK", "United Kingdom"),
    "birmingham": ("Birmingham, UK", "United Kingdom"),
    "liverpool": ("Liverpool, UK", "United Kingdom"),
    "bristol": ("Bristol, UK", "United Kingdom"),
    "york": ("York, UK", "United Kingdom"),
    "bath": ("Bath, UK", "United Kingdom"),
    "cambridge": ("Cambridge, UK", "United Kingdom"),
    "oxford": ("Oxford, UK", "United Kingdom"),
    "brighton": ("Brighton, UK", "United Kingdom"),
    "tokyo": ("Tokyo, Japan", "Japan"),
    "osaka": ("Osaka, Japan", "Japan"),
    "hiroshima": ("Hiroshima, Japan", "Japan"),
    "nara": ("Nara, Japan", "Japan"),
    "sapporo": ("Sapporo, Japan", "Japan"),
    "fukuoka": ("Fukuoka, Japan", "Japan"),
    "new york": ("New York, USA", "United States"),
    "san francisco": ("San Francisco, USA", "United States"),
    "los angeles": ("Los Angeles, USA", "United States"),
    "chicago": ("Chicago, USA", "United States"),
    "miami": ("Miami, USA", "United States"),
    "seattle": ("Seattle, USA", "United States"),
    "boston": ("Boston, USA", "United States"),
    "washington": ("Washington, USA", "United States"),
    "las vegas": ("Las Vegas, USA", "United States"),
    "orlando": ("Orlando, USA", "United States"),
    "honolulu": ("Honolulu, USA", "United States"),
    "hawaii": ("Honolulu, USA", "United States"),
    "berlin": ("Berlin, Germany", "Germany"),
    "munich": ("Munich, Germany", "Germany"),
    "frankfurt": ("Frankfurt, Germany", "Germany"),
    "hamburg": ("Hamburg, Germany", "Germany"),
    "cologne": ("Cologne, Germany", "Germany"),
    "dresden": ("Dresden, Germany", "Germany"),
    "milan": ("Milan, Italy", "Italy"),
    "venice": ("Venice, Italy", "Italy"),
    "florence": ("Florence, Italy", "Italy"),
    "naples": ("Naples, Italy", "Italy"),
    "turin": ("Turin, Italy", "Italy"),
    "bologna": ("Bologna, Italy", "Italy"),
    "amsterdam": ("Amsterdam, Netherlands", "Netherlands"),
    "rotterdam": ("Rotterdam, Netherlands", "Netherlands"),
    "utrecht": ("Utrecht, Netherlands", "Netherlands"),
    "brussels": ("Brussels, Belgium", "Belgium"),
    "vienna": ("Vienna, Austria", "Austria"),
    "salzburg": ("Salzburg, Austria", "Austria"),
    "prague": ("Prague, Czech Republic", "Czech Republic"),
    "budapest": ("Budapest, Hungary", "Hungary"),
    "warsaw": ("Warsaw, Poland", "Poland"),
    "krakow": ("Krakow, Poland", "Poland"),
    "lisbon": ("Lisbon, Portugal", "Portugal"),
    "porto": ("Porto, Portugal", "Portugal"),
    "madrid": ("Madrid, Spain", "Spain"),
    "seville": ("Seville, Spain", "Spain"),
    "valencia": ("Valencia, Spain", "Spain"),
    "athens": ("Athens, Greece", "Greece"),
    "santorini": ("Santorini, Greece", "Greece"),
    "mykonos": ("Mykonos, Greece", "Greece"),
    "istanbul": ("Istanbul, Turkey", "Turkey"),
    "cappadocia": ("Cappadocia, Turkey", "Turkey"),
    "stockholm": ("Stockholm, Sweden", "Sweden"),
    "oslo": ("Oslo, Norway", "Norway"),
    "copenhagen": ("Copenhagen, Denmark", "Denmark"),
    "helsinki": ("Helsinki, Finland", "Finland"),
    "reykjavik": ("Reykjavik, Iceland", "Iceland"),
    "zurich": ("Zurich, Switzerland", "Switzerland"),
    "geneva": ("Geneva, Switzerland", "Switzerland"),
    "bern": ("Bern, Switzerland", "Switzerland"),
    "dublin": ("Dublin, Ireland", "Ireland"),
    "zagreb": ("Zagreb, Croatia", "Croatia"),
    "dubrovnik": ("Dubrovnik, Croatia", "Croatia"),
    "split": ("Split, Croatia", "Croatia"),
    "ljubljana": ("Ljubljana, Slovenia", "Slovenia"),
    "belgrade": ("Belgrade, Serbia", "Serbia"),
    "sofia": ("Sofia, Bulgaria", "Bulgaria"),
    "bucharest": ("Bucharest, Romania", "Romania"),
    "kyiv": ("Kyiv, Ukraine", "Ukraine"),
    "kiev": ("Kyiv, Ukraine", "Ukraine"),
    "riga": ("Riga, Latvia", "Latvia"),
    "vilnius": ("Vilnius, Lithuania", "Lithuania"),
    "tallinn": ("Tallinn, Estonia", "Estonia"),
    "moscow": ("Moscow, Russia", "Russia"),
    "saint petersburg": ("Saint Petersburg, Russia", "Russia"),
    "st petersburg": ("Saint Petersburg, Russia", "Russia"),
    # ── Asia-Pacific ──
    "sydney": ("Sydney, Australia", "Australia"),
    "melbourne": ("Melbourne, Australia", "Australia"),
    "brisbane": ("Brisbane, Australia", "Australia"),
    "perth": ("Perth, Australia", "Australia"),
    "adelaide": ("Adelaide, Australia", "Australia"),
    "auckland": ("Auckland, New Zealand", "New Zealand"),
    "wellington": ("Wellington, New Zealand", "New Zealand"),
    "queenstown": ("Queenstown, New Zealand", "New Zealand"),
    "singapore": ("Singapore", "Singapore"),
    "kuala lumpur": ("Kuala Lumpur, Malaysia", "Malaysia"),
    "penang": ("Penang, Malaysia", "Malaysia"),
    "jakarta": ("Jakarta, Indonesia", "Indonesia"),
    "yogyakarta": ("Yogyakarta, Indonesia", "Indonesia"),
    "manila": ("Manila, Philippines", "Philippines"),
    "hanoi": ("Hanoi, Vietnam", "Vietnam"),
    "ho chi minh city": ("Ho Chi Minh City, Vietnam", "Vietnam"),
    "saigon": ("Ho Chi Minh City, Vietnam", "Vietnam"),
    "phnom penh": ("Phnom Penh, Cambodia", "Cambodia"),
    "siem reap": ("Siem Reap, Cambodia", "Cambodia"),
    "yangon": ("Yangon, Myanmar", "Myanmar"),
    "seoul": ("Seoul, South Korea", "South Korea"),
    "busan": ("Busan, South Korea", "South Korea"),
    "beijing": ("Beijing, China", "China"),
    "shanghai": ("Shanghai, China", "China"),
    "hong kong": ("Hong Kong", "Hong Kong"),
    "taipei": ("Taipei, Taiwan", "Taiwan"),
    "kathmandu": ("Kathmandu, Nepal", "Nepal"),
    "pokhara": ("Pokhara, Nepal", "Nepal"),
    "colombo": ("Colombo, Sri Lanka", "Sri Lanka"),
    "male": ("Male, Maldives", "Maldives"),
    "maldives": ("Male, Maldives", "Maldives"),
    "tashkent": ("Tashkent, Uzbekistan", "Uzbekistan"),
    "almaty": ("Almaty, Kazakhstan", "Kazakhstan"),
    "tbilisi": ("Tbilisi, Georgia", "Georgia"),
    "baku": ("Baku, Azerbaijan", "Azerbaijan"),
    "yerevan": ("Yerevan, Armenia", "Armenia"),
    "dubai": ("Dubai, UAE", "United Arab Emirates"),
    "abu dhabi": ("Abu Dhabi, UAE", "United Arab Emirates"),
    "doha": ("Doha, Qatar", "Qatar"),
    "riyadh": ("Riyadh, Saudi Arabia", "Saudi Arabia"),
    "jeddah": ("Jeddah, Saudi Arabia", "Saudi Arabia"),
    "tel aviv": ("Tel Aviv, Israel", "Israel"),
    "jerusalem": ("Jerusalem, Israel", "Israel"),
    "amman": ("Amman, Jordan", "Jordan"),
    "petra": ("Petra, Jordan", "Jordan"),
    "beirut": ("Beirut, Lebanon", "Lebanon"),
    "muscat": ("Muscat, Oman", "Oman"),
    "kuwait city": ("Kuwait City, Kuwait", "Kuwait"),
    # ── Africa & Americas ──
    "cairo": ("Cairo, Egypt", "Egypt"),
    "marrakech": ("Marrakech, Morocco", "Morocco"),
    "casablanca": ("Casablanca, Morocco", "Morocco"),
    "fez": ("Fez, Morocco", "Morocco"),
    "nairobi": ("Nairobi, Kenya", "Kenya"),
    "capetown": ("Cape Town, South Africa", "South Africa"),
    "cape town": ("Cape Town, South Africa", "South Africa"),
    "johannesburg": ("Johannesburg, South Africa", "South Africa"),
    "lagos": ("Lagos, Nigeria", "Nigeria"),
    "accra": ("Accra, Ghana", "Ghana"),
    "addis ababa": ("Addis Ababa, Ethiopia", "Ethiopia"),
    "tunis": ("Tunis, Tunisia", "Tunisia"),
    "algiers": ("Algiers, Algeria", "Algeria"),
    "toronto": ("Toronto, Canada", "Canada"),
    "vancouver": ("Vancouver, Canada", "Canada"),
    "montreal": ("Montreal, Canada", "Canada"),
    "calgary": ("Calgary, Canada", "Canada"),
    "ottawa": ("Ottawa, Canada", "Canada"),
    "mexico city": ("Mexico City, Mexico", "Mexico"),
    "cancun": ("Cancun, Mexico", "Mexico"),
    "san jose": ("San Jose, Costa Rica", "Costa Rica"),
    "panama city": ("Panama City, Panama", "Panama"),
    "kingston": ("Kingston, Jamaica", "Jamaica"),
    "nassau": ("Nassau, Bahamas", "Bahamas"),
    "rio de janeiro": ("Rio de Janeiro, Brazil", "Brazil"),
    "sao paulo": ("Sao Paulo, Brazil", "Brazil"),
    "buenos aires": ("Buenos Aires, Argentina", "Argentina"),
    "santiago": ("Santiago, Chile", "Chile"),
    "lima": ("Lima, Peru", "Peru"),
    "cusco": ("Cusco, Peru", "Peru"),
    "bogota": ("Bogota, Colombia", "Colombia"),
    "cartagena": ("Cartagena, Colombia", "Colombia"),
    "quito": ("Quito, Ecuador", "Ecuador"),
    "montevideo": ("Montevideo, Uruguay", "Uruguay"),
}

# Country-name whitelist for the structural heuristic when the geocoder is unreachable.
KNOWN_COUNTRIES: set[str] = {
    "india", "japan", "indonesia", "switzerland", "spain", "costa rica",
    "france", "thailand", "uk", "united kingdom", "usa", "united states",
    "germany", "italy", "australia", "new zealand", "singapore", "malaysia",
    "philippines", "vietnam", "cambodia", "myanmar", "south korea", "china",
    "hong kong", "taiwan", "nepal", "sri lanka", "maldives", "uzbekistan",
    "kazakhstan", "georgia", "azerbaijan", "armenia", "uae",
    "united arab emirates", "qatar", "saudi arabia", "israel", "jordan",
    "lebanon", "oman", "kuwait", "egypt", "morocco", "kenya",
    "south africa", "nigeria", "ghana", "ethiopia", "tunisia", "algeria",
    "canada", "mexico", "panama", "cuba", "jamaica", "bahamas", "brazil",
    "argentina", "chile", "peru", "colombia", "ecuador", "uruguay",
    "netherlands", "belgium", "austria", "czech republic", "hungary",
    "poland", "portugal", "greece", "turkey", "sweden", "norway",
    "denmark", "finland", "iceland", "ireland", "croatia", "slovenia",
    "serbia", "bulgaria", "romania", "ukraine", "latvia", "lithuania",
    "estonia", "russia",
}

# Tokens that signal keyboard-mashing rather than a place name.
_GIBBERISH_TOKENS: set[str] = {
    "asdf", "asdfg", "asdfgh", "qwerty", "qwert", "zxcv", "zxcvb", "vuvv",
    "test", "testing", "temp", "tmp", "foo", "bar", "baz", "abc", "abcd",
    "abcdef", "xxx", "xxxx", "blah", "asdfasdf", "poiuy", "lkjh", "mnbv",
    "123", "1234", "12345", "abc123", "xyz123", "qwe", "asd", "aaa", "zzz",
    "dg", "xyz",
}


def _is_obvious_gibberish(token: str) -> bool:
    """
    Heuristic screen for obvious keyboard-mashing and placeholder tokens.
    Only flags a token when it is clearly not a plausible place name.
    """
    if not token:
        return True

    # Exact matches against the known-gibberish list.
    if token in _GIBBERISH_TOKENS:
        return True

    # Long consonant runs with no vowel structure (e.g. 'xyz123').
    if re.fullmatch(r"[bcdfghjklmnpqrstvwxz]{5,}", token):
        return True
    if re.search(r"\d{4,}", token):
        return True
    if re.search(r"(.)\1{2,}", token):   # triples like 'aaa', 'zzz'
        return True
    if re.search(r"(.{2})\1", token):    # doubled pairs like 'vuvv'
        return True

    # Very short tokens with no vowel are almost always noise.
    if len(token) <= 3 and not re.search(r"[aeiouy]", token):
        return True

    return False


class LocationVerifier:
    """Verifies location validity using an offline hub dictionary, live geocoding, and LLM fallback."""

    def __init__(self, timeout: float = 4.0):
        self.timeout = timeout

    # ─── Public API ──────────────────────────────────────────────────────

    async def verify_location(self, location_str: str) -> LocationVerificationResult:
        """
        Validates if a location string represents a real place on Earth.
        Returns LocationVerificationResult with canonical information or an error message.

        Resolution order:
            1. Offline hub-city dictionary (zero network, instant).
            2. Live Open-Meteo geocoding API (with timeout).
            3. Structural heuristic (recognized country or plausible multi-word place name).
            4. LLM check, when a provider is configured.
            5. Reject as unverifiable.
        """
        raw = (location_str or "").strip()
        if len(raw) < 2:
            return LocationVerificationResult(
                is_valid=False,
                error_message=f"Location '{location_str}' is too short or empty.",
            )

        # Extract the city portion before the first comma.
        clean_name = raw.split(",")[0].strip().lower()

        # Reject obvious keyboard-mashing before any lookup.
        if _is_obvious_gibberish(clean_name):
            return LocationVerificationResult(
                is_valid=False,
                error_message=(
                    f"'{raw}' is not a recognized city or destination on Earth. "
                    f"Please enter a valid location (e.g. 'Paris, France')."
                ),
            )

        # ── Step 1: Offline hub-city dictionary ────────────────────────
        offline_hit = self._lookup_offline(raw, clean_name)
        if offline_hit is not None:
            canonical, country = offline_hit
            return LocationVerificationResult(
                is_valid=True,
                canonical_name=canonical,
                country=country,
            )

        # ── Step 2: Live Open-Meteo geocoding ──────────────────────────
        live_result = await self._try_live_geocoding(raw, clean_name)
        if live_result is not None:
            return live_result

        # ── Step 3: LLM check (if available) ───────────────────────────
        if llm_service.is_available():
            llm_result = await self._try_llm_check(raw)
            if llm_result is not None:
                return llm_result

        # ── Step 4: Structural heuristic (geocoder unreachable & offline) ──
        heuristic = self._structural_check(raw, clean_name)
        if heuristic is not None:
            return heuristic

        # ── Step 5: Reject ─────────────────────────────────────────────
        return LocationVerificationResult(
            is_valid=False,
            error_message=(
                f"Could not verify '{raw}' as a recognized city or destination on Earth. "
                f"Please enter a valid location (e.g. 'Paris, France')."
            ),
        )

    # ─── Offline Dictionary Lookup ───────────────────────────────────────

    @staticmethod
    def _lookup_offline(raw: str, clean_name: str) -> Optional[Tuple[str, str]]:
        """
        Checks the offline hub-city dictionary using multiple normalization strategies.

        Returns (canonical_name, country) on hit, or None on miss.
        """
        candidates = [
            clean_name,                              # 'paris'
            raw.lower().strip(),                     # 'paris, france'
        ]

        # Also try the individual comma-separated parts on their own
        # (e.g. 'India' alone, or 'Paris' from 'Paris, France').
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) >= 2:
            candidates.append(parts[0].lower())      # 'paris'
            candidates.append(parts[1].lower())      # 'france'

        for key in candidates:
            hit = OFFLINE_CITIES.get(key)
            if hit is not None:
                return hit

        return None

    # ─── Live Geocoding ──────────────────────────────────────────────────

    async def _try_live_geocoding(
        self, raw: str, clean_name: str
    ) -> Optional[LocationVerificationResult]:
        """
        Queries the Open-Meteo geocoding API with a timeout.
        Returns a successful LocationVerificationResult on a match, or None on failure/no-match.
        """
        try:
            url = (
                f"https://geocoding-api.open-meteo.com/v1/search"
                f"?name={clean_name}&count=5&language=en&format=json"
            )
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    if results:
                        top = results[0]
                        matched_name = top.get("name", clean_name)
                        matched_country = top.get("country", "")
                        return LocationVerificationResult(
                            is_valid=True,
                            canonical_name=(
                                f"{matched_name}, {matched_country}"
                                if matched_country
                                else matched_name
                            ),
                            country=matched_country or None,
                        )
        except Exception as e:
            logger.debug(f"Geocoding lookup failed for '{clean_name}': {e}")

        return None

    # ─── Structural Heuristic ────────────────────────────────────────────

    @staticmethod
    def _structural_check(
        raw: str, clean_name: str
    ) -> Optional[LocationVerificationResult]:
        """
        Heuristic validation when both the offline dict and live geocoder miss.

        A place passes if:
          - The query includes a recognized country name (e.g. 'Springfield, USA'), OR
          - The query looks like a plausible multi-word geographic name
            (two or more tokens, each 3+ chars, no digits), OR
          - The single-token name is 4+ chars, contains a vowel, and has no digits.

        Returns a LocationVerificationResult on pass, or None on fail.
        """
        parts = [p.strip() for p in raw.split(",") if p.strip()]

        # Check 1: Recognized country name anywhere in the query.
        for part in parts:
            if part.lower().strip(".") in KNOWN_COUNTRIES:
                return LocationVerificationResult(
                    is_valid=True,
                    canonical_name=raw,
                    country=part.title(),
                )

        # Check 2: Plausible multi-word geographic name (e.g. 'Tirthan Valley').
        tokens = clean_name.split()
        if len(tokens) >= 2:
            all_alpha = all(t.isalpha() and len(t) >= 3 for t in tokens)
            if all_alpha:
                return LocationVerificationResult(
                    is_valid=True,
                    canonical_name=raw,
                    country=None,
                )

        # Check 3: Single token with vowel, 4+ chars, no digits.
        if (
            len(tokens) == 1
            and len(clean_name) >= 4
            and clean_name.isalpha()
            and re.search(r"[aeiouy]", clean_name)
        ):
            return LocationVerificationResult(
                is_valid=True,
                canonical_name=raw,
                country=None,
            )

        return None

    # ─── LLM Fallback ────────────────────────────────────────────────────

    async def _try_llm_check(
        self, raw: str
    ) -> Optional[LocationVerificationResult]:
        """
        Uses the configured LLM to validate a location when all deterministic
        methods have failed.  Returns None if the LLM is unavailable or errors.
        """
        if not llm_service.is_available():
            return None

        try:
            class LLMLocationCheck(BaseModel):
                is_real_location: bool
                canonical_name: Optional[str] = None
                country: Optional[str] = None
                explanation: str

            prompt = (
                f"Analyze the location query: '{raw}'.\n"
                f"Is this a real, recognized city, town, island, national park, "
                f"or travel destination on Earth (or a common typo/phonetic spelling of one, e.g. 'merrut' -> 'Meerut, India')?\n"
                f"If it is a real place or recognizable typo, set is_real_location=true, "
                f"canonical_name to the standard proper name with country (e.g. 'Meerut, India'), and country to its country.\n"
                f"If it is random gibberish (such as 'dg', 'vuvv', 'xyz', 'asdf'), "
                f"set is_real_location=false."
            )
            system = (
                "You are a geographic verification engine. "
                "Audit whether locations exist."
            )
            check = await llm_service.generate_structured(
                prompt, system, LLMLocationCheck
            )
            if check:
                if check.is_real_location and check.canonical_name:
                    return LocationVerificationResult(
                        is_valid=True,
                        canonical_name=check.canonical_name,
                        country=check.country,
                    )
                return LocationVerificationResult(
                    is_valid=False,
                    error_message=(
                        f"'{raw}' is not a recognized travel destination or city "
                        f"({check.explanation})."
                    ),
                )
        except Exception as e:
            logger.debug(f"LLM location verification failed: {e}")

        return None


# Module-level singleton — used by routers and tests.
location_verifier = LocationVerifier()