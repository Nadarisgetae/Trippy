"""
TRIPPY Backend — Tests for Google Search & Outstation Pricing Service
"""

import pytest
from app.integrations.search import search_pricing_service
from app.schemas.trip import TransportMode
from app.tools.transport_tools import estimate_transport


@pytest.mark.anyio
async def test_search_pricing_service_car_group_scaling():
    # 1. 11 travelers to Amroha (145.9 km) -> Should recommend Tempo Traveller Minibus (~₹8,600 round trip)
    quote_11 = await search_pricing_service.lookup_transit_fare(
        origin="New Delhi, India",
        destination="Amroha, India",
        mode=TransportMode.car,
        travelers=11,
        distance_km=145.9,
        currency="INR",
    )
    assert quote_11.one_way_cost > 3500.0
    assert quote_11.one_way_cost < 6000.0
    assert "Tempo Traveller" in quote_11.vehicle_or_class
    assert "Verified Outstation Cab Tariff & Google Search" in quote_11.notes

    # 2. 2 travelers to Meerut (70 km) -> Should recommend Sedan
    quote_2 = await search_pricing_service.lookup_transit_fare(
        origin="New Delhi, India",
        destination="Meerut, India",
        mode=TransportMode.car,
        travelers=2,
        distance_km=70.0,
        currency="INR",
    )
    assert quote_2.one_way_cost >= 1800.0
    assert quote_2.one_way_cost <= 2500.0
    assert "Sedan" in quote_2.vehicle_or_class


@pytest.mark.anyio
async def test_search_pricing_service_train_fares():
    # Train fare for 11 travelers between Delhi and Amroha (145.9 km)
    quote_train = await search_pricing_service.lookup_transit_fare(
        origin="New Delhi, India",
        destination="Amroha, India",
        mode=TransportMode.train,
        travelers=11,
        distance_km=145.9,
        currency="INR",
    )
    assert quote_train.one_way_cost == 1980.0  # 11 * 180
    assert quote_train.round_trip_cost == 3960.0
    assert "IRCTC" in quote_train.notes


def test_estimate_transport_car_never_multiplies_vehicle_by_passengers():
    res_11 = estimate_transport(
        origin="New Delhi, India",
        destination="Amroha, India",
        preferred_mode=TransportMode.car,
        travelers=11,
        currency="INR",
        distance_km=145.9,
    )
    # Previously was ₹35,200 (11 * ₹3,200). Now ~₹8,603 total round trip!
    assert res_11.total_cost < 10000.0
    assert res_11.legs[0].cost_estimate < 5000.0
    assert "Tempo Traveller" in res_11.legs[0].notes
