"""
TRIPPY Backend — Real-World Places & Landmarks Integration Service

Discovers authentic points of interest, cultural landmarks, monuments,
and destination summaries using Wikipedia Geosearch & REST APIs.
Provides real-world attractions and context for any geocoded location worldwide,
with rich offline knowledge for instant, reliable fallback.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Dict, List, Optional, Tuple
import httpx

from app.integrations.maps.service import CITY_COORDINATES

logger = logging.getLogger("trippy.places")


@dataclass
class PlacePOI:
    name: str
    description: str = ""
    distance_meters: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_url: Optional[str] = None


@dataclass
class DestinationInfo:
    title: str
    summary: str
    coordinates: Optional[Tuple[float, float]] = None
    landmarks: List[PlacePOI] = field(default_factory=list)


OFFLINE_SUMMARIES: Dict[str, str] = {
    "agra": "Agra is a city on the banks of the Yamuna river in the Indian state of Uttar Pradesh. It is a major tourist destination owing to its magnificent Mughal-era buildings, most notably the Taj Mahal, Agra Fort, and Fatehpur Sikri, all three of which are UNESCO World Heritage Sites.",
    "amroha": "Amroha is a historic city in Uttar Pradesh, known for its mangoes, traditional music instruments, and Sufi shrines including Dargah Shah Wilayat.",
    "meerut": "Meerut is an ancient city in western Uttar Pradesh with settlements dating to the Indus Valley Civilization. It was the major starting point of the Indian Rebellion of 1857.",
    "ghaziabad": "Ghaziabad is a major industrial and planned city in Uttar Pradesh, part of the National Capital Region (NCR) adjacent to New Delhi.",
    "new delhi": "New Delhi is the capital of India and seat of all three branches of the Government of India, famed for Mughal monuments and British colonial architecture.",
    "delhi": "Delhi is a sprawling metropolitan region in northern India featuring centuries of history, from Old Delhi's Mughal Red Fort to modern urban centers.",
    "jaipur": "Jaipur is the capital of Rajasthan, founded in 1727 by Maharaja Sawai Jai Singh II. Known as the 'Pink City' for its terracotta-hued buildings, it is a UNESCO World Heritage site.",
    "varanasi": "Varanasi is a sacred city on the Ganges river in Uttar Pradesh, revered as the spiritual capital of India with ancient ghats and temples.",
    "haridwar": "Haridwar is an ancient pilgrimage city in Uttarakhand where the sacred Ganges River emerges from the Himalayan foothills.",
    "kasol": "Kasol is a picturesque hamlet in the Parvati Valley of Himachal Pradesh, celebrated for pine forests, riverside cafes, and trekking trails.",
    "kyoto": "Kyoto is the ancient cultural capital of Japan on the island of Honshu, renowned for classical Buddhist temples, gardens, and imperial palaces.",
    "rome": "Rome is the capital city of Italy, famed for nearly three millennia of globally influential art, architecture, and ruins of the Roman Empire.",
    "paris": "Paris is France's capital, a global hub for art, fashion, gastronomy, and culture, defined by 19th-century cityscapes and the Seine river.",
    "bali": "Bali is an Indonesian province known for its forested volcanic mountains, iconic rice paddies, beaches, and coral reefs.",
    "bhopal": "Bhopal is the capital city of Madhya Pradesh, known as the 'City of Lakes' for its various natural and artificial lakes including Bhojtal (Upper Lake). Founded in the 11th century by Paramara king Raja Bhoj and ruled for over a century by visionary female monarchs (Begums of Bhopal), it is a major cultural and historical center near UNESCO sites Sanchi and Bhimbetka.",
}

OFFLINE_LANDMARKS: Dict[str, List[PlacePOI]] = {
    "agra": [
        PlacePOI(
            name="Taj Mahal",
            description="UNESCO World Heritage 17th-century white marble mausoleum commissioned by Mughal Emperor Shah Jahan for Mumtaz Mahal.",
            distance_meters=800.0,
            source_url="https://en.wikipedia.org/wiki/Taj_Mahal",
        ),
        PlacePOI(
            name="Agra Fort",
            description="UNESCO World Heritage imperial red sandstone fortress containing Jahangiri Mahal, Diwan-i-Khas, and Shah Jahan's prison tower.",
            distance_meters=2500.0,
            source_url="https://en.wikipedia.org/wiki/Agra_Fort",
        ),
        PlacePOI(
            name="Fatehpur Sikri",
            description="Fortified Mughal capital founded by Emperor Akbar in 1571, featuring Buland Darwaza and the white marble Tomb of Salim Chishti.",
            distance_meters=35000.0,
            source_url="https://en.wikipedia.org/wiki/Fatehpur_Sikri",
        ),
        PlacePOI(
            name="Mehtab Bagh",
            description="Charbagh garden complex on the northern bank of Yamuna River, perfectly aligned with the Taj Mahal for sunset reflections.",
            distance_meters=1800.0,
            source_url="https://en.wikipedia.org/wiki/Mehtab_Bagh",
        ),
        PlacePOI(
            name="Tomb of I'timād-ud-Daulah",
            description="Jewel-box white marble mausoleum built by Empress Nur Jahan, widely celebrated as the architectural precursor to the Taj Mahal.",
            distance_meters=3200.0,
            source_url="https://en.wikipedia.org/wiki/Tomb_of_I%27tim%C4%81d-ud-Daulah",
        ),
        PlacePOI(
            name="Kinari Bazaar & Sadar Bazaar",
            description="Historic bazaars of Agra renowned for authentic Mughlai food, Agra Angoori petha, marble handicrafts, and leather goods.",
            distance_meters=3000.0,
            source_url="https://en.wikipedia.org/wiki/Agra#Cuisine",
        ),
    ],
    "amroha": [
        PlacePOI(
            name="Dargah Shah Wilayat",
            description="Revered 13th-century Sufi shrine dedicated to Hazrat Shah Wilayat, famous for peaceful scorpion legend and historic architecture.",
            distance_meters=600.0,
            source_url="https://en.wikipedia.org/wiki/Amroha",
        ),
        PlacePOI(
            name="Vasudev Mandir",
            description="Ancient Hindu temple complex dedicated to Lord Krishna and Vasudeva with sacred kund and annual cultural festival.",
            distance_meters=1200.0,
            source_url="https://en.wikipedia.org/wiki/Amroha",
        ),
        PlacePOI(
            name="Sadat Gate & Amroha Fort Grounds",
            description="Mughal era monumental gateway and heritage ramparts reflecting Amroha's medieval strategic importance.",
            distance_meters=1500.0,
            source_url="https://en.wikipedia.org/wiki/Amroha",
        ),
    ],
    "meerut": [
        PlacePOI(
            name="Augharnath Temple (Kali Paltan Mandir)",
            description="Historic Shiva temple where Indian soldiers planned the May 10, 1857 uprising against the British East India Company.",
            distance_meters=1200.0,
            source_url="https://en.wikipedia.org/wiki/Augharnath_Temple",
        ),
        PlacePOI(
            name="St. John's Church, Meerut",
            description="Historic Anglican parish church built in 1819, among the oldest existing churches in northern India.",
            distance_meters=2000.0,
            source_url="https://en.wikipedia.org/wiki/St._John%27s_Church,_Meerut",
        ),
        PlacePOI(
            name="Sardhana Basilica of Our Lady of Graces",
            description="Roman Catholic minor basilica built in 1822 by Begum Samru, showcasing stunning Italianate neoclassical architecture.",
            distance_meters=18000.0,
            source_url="https://en.wikipedia.org/wiki/Basilica_of_Our_Lady_of_Graces",
        ),
    ],
    "bhopal": [
        PlacePOI(
            name="Taj-ul-Masajid",
            description="One of Asia's largest mosques featuring 18-storey octagonal pink minarets, massive white domes, and a 21,000 m² marble courtyard commissioned by Nawab Shah Jahan Begum.",
            distance_meters=2000.0,
            source_url="https://en.wikipedia.org/wiki/Taj-ul-Masajid",
        ),
        PlacePOI(
            name="Upper Lake (Bhojtal) & Van Vihar National Park",
            description="Asia's largest artificial lake commissioned in the 11th century by Paramara King Raja Bhoj, with scenic sunset boat cruises and an adjacent open-air wildlife safari park.",
            distance_meters=1500.0,
            source_url="https://en.wikipedia.org/wiki/Bhojtal",
        ),
        PlacePOI(
            name="Sanchi Stupa (UNESCO World Heritage Site)",
            description="Monumental 3rd-century BCE Buddhist sanctuary commissioned by Emperor Ashoka, showcasing the Great Stupa and intricately carved torana gateways depicting Jataka tales.",
            distance_meters=46000.0,
            source_url="https://en.wikipedia.org/wiki/Sanchi",
        ),
        PlacePOI(
            name="Bhimbetka Rock Shelters (UNESCO World Heritage Site)",
            description="Prehistoric archaeological complex featuring 750 rock shelters with 30,000-year-old Paleolithic cave art depicting hunting, animals, and primordial community dances.",
            distance_meters=45000.0,
            source_url="https://en.wikipedia.org/wiki/Bhimbetka_rock_shelters",
        ),
        PlacePOI(
            name="Madhya Pradesh Tribal Museum",
            description="World-renowned experiential museum showcasing life-size indigenous homes, Gond and Bhil murals, mythic installations, and traditional tribal craft.",
            distance_meters=3500.0,
            source_url="https://en.wikipedia.org/wiki/Madhya_Pradesh_Tribal_Museum",
        ),
        PlacePOI(
            name="Chowk Bazaar & Sarafa Mughlai Food Trail",
            description="Historic culinary street walk through the old walled city of Bhopal tasting Bhopali gosht korma, crisp poha-jalebi, Sulaimani chai, and mawa jalebi.",
            distance_meters=1800.0,
            source_url="https://en.wikipedia.org/wiki/Bhopal#Cuisine",
        ),
    ],
}


class PlacesService:
    """Fetches real-world landmarks and tourist highlights using Wikipedia Geosearch and offline fallback."""

    def __init__(self, timeout: float = 4.0, cache_ttl: int = 86400):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._headers = {
            "User-Agent": "TrippyTravelPlanner/1.0 (https://github.com/trippy/trippy; info@trippy.local)"
        }
        self._cache: Dict[str, Tuple[float, DestinationInfo]] = {}

    async def get_destination_info(
        self,
        city_name: str,
        coordinates: Optional[Tuple[float, float]] = None,
    ) -> Optional[DestinationInfo]:
        """
        Retrieves real-world summary and nearby landmarks for a destination.
        """
        clean_name = city_name.split(",")[0].strip()
        cache_key = clean_name.lower()

        now = time.time()
        if cache_key in self._cache:
            ts, info = self._cache[cache_key]
            if now - ts < self.cache_ttl:
                return info

        summary_text = OFFLINE_SUMMARIES.get(cache_key, "")
        resolved_coords = coordinates or CITY_COORDINATES.get(cache_key)

        # 1. Fetch live Wikipedia Page Summary for the city/destination
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_name.replace(' ', '_')}"
            async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    summary_text = data.get("extract", summary_text)
                    if not resolved_coords and "coordinates" in data:
                        resolved_coords = (
                            float(data["coordinates"]["lat"]),
                            float(data["coordinates"]["lon"]),
                        )
        except Exception as e:
            logger.debug(f"Wiki summary failed for {clean_name}: {e}")

        # 2. Fetch Nearby Points of Interest via Wikipedia Geosearch
        landmarks: List[PlacePOI] = []
        if resolved_coords:
            lat, lon = resolved_coords
            try:
                geo_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "geosearch",
                    "gscoord": f"{lat}|{lon}",
                    "gsradius": 15000,  # 15km radius
                    "gslimit": 12,
                    "format": "json",
                }
                async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
                    geo_res = await client.get(geo_url, params=params)
                    if geo_res.status_code == 200:
                        results = geo_res.json().get("query", {}).get("geosearch", [])
                        for item in results:
                            title = item.get("title", "")
                            if title.lower() != clean_name.lower():
                                landmarks.append(
                                    PlacePOI(
                                        name=title,
                                        distance_meters=float(item.get("dist", 0.0)),
                                        latitude=float(item.get("lat", 0.0)),
                                        longitude=float(item.get("lon", 0.0)),
                                        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                    )
                                )
            except Exception as e:
                logger.debug(f"Wiki geosearch failed for {clean_name}: {e}")

        # If live search returned no landmarks, use curated offline landmarks
        if not landmarks and cache_key in OFFLINE_LANDMARKS:
            landmarks = list(OFFLINE_LANDMARKS[cache_key])

        info = DestinationInfo(
            title=clean_name,
            summary=summary_text,
            coordinates=resolved_coords,
            landmarks=landmarks,
        )
        self._cache[cache_key] = (now, info)
        return info


places_service = PlacesService()
