"""
TRIPPY Backend — Sequential Multi-Agent Stages Tests

Tests each of the 5 stage endpoints:
1. POST /api/trips/stages/destination
2. POST /api/trips/stages/transport
3. POST /api/trips/stages/stay-activity
4. POST /api/trips/stages/budget
5. POST /api/trips/stages/itinerary
"""

from datetime import date, timedelta
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_stage_1_destination():
    payload = {
        "origin": "New Delhi, India",
        "destinations": ["Kyoto, Japan"],
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=10)),
        "budget_max": 2500,
        "currency": "USD",
        "travel_style": "cultural",
        "interests": ["temples", "food"],
    }
    res = client.post("/api/trips/stages/destination", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["selected_destination"] == "Kyoto, Japan"
    assert len(data["candidates"]) >= 1


def test_stage_2_transport():
    payload = {
        "origin": "New Delhi, India",
        "destination": "Kyoto, Japan",
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=10)),
        "travelers": 2,
        "preferred_transport": "flight",
        "travel_style": "cultural",
        "currency": "USD",
    }
    res = client.post("/api/trips/stages/transport", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "transport" in data
    assert len(data["transport"]["legs"]) >= 1
    assert data["transport"]["total_cost"] > 0


def test_stage_3_stay_activity():
    payload = {
        "destination": "Kyoto, Japan",
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=10)),
        "travelers": 2,
        "travel_style": "cultural",
        "interests": ["temples", "food"],
        "currency": "USD",
    }
    res = client.post("/api/trips/stages/stay-activity", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "stay_activity" in data
    assert data["stay_activity"]["accommodation_name"]
    assert len(data["stay_activity"]["activities"]) >= 1


def test_stage_4_budget():
    payload = {
        "transport_cost": 800.0,
        "accommodation_cost": 600.0,
        "activities_cost": 250.0,
        "food_cost": 400.0,
        "budget_max": 2500.0,
        "currency": "USD",
    }
    res = client.post("/api/trips/stages/budget", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_within_budget"] is True
    assert data["breakdown"]["transport"] == 800.0
    assert data["breakdown"]["total"] > 2050.0  # includes 8% contingency


def test_stage_5_itinerary_and_persistence():
    # Run stage 1 to 4 to gather data
    today = date.today()
    start_str = str(today + timedelta(days=5))
    end_str = str(today + timedelta(days=10))

    dest_res = client.post("/api/trips/stages/destination", json={
        "origin": "New Delhi, India",
        "destinations": ["Kyoto, Japan"],
        "start_date": start_str,
        "end_date": end_str,
        "budget_max": 3000,
        "currency": "USD",
        "travel_style": "cultural",
        "interests": ["temples"],
    }).json()

    trans_res = client.post("/api/trips/stages/transport", json={
        "origin": "New Delhi, India",
        "destination": "Kyoto, Japan",
        "start_date": start_str,
        "end_date": end_str,
        "travelers": 2,
        "preferred_transport": "flight",
        "travel_style": "cultural",
        "currency": "USD",
    }).json()

    stay_res = client.post("/api/trips/stages/stay-activity", json={
        "destination": "Kyoto, Japan",
        "start_date": start_str,
        "end_date": end_str,
        "travelers": 2,
        "travel_style": "cultural",
        "interests": ["temples"],
        "currency": "USD",
    }).json()

    budget_res = client.post("/api/trips/stages/budget", json={
        "transport_cost": trans_res["transport"]["total_cost"],
        "accommodation_cost": stay_res["stay_activity"]["total_accommodation_cost"],
        "activities_cost": stay_res["stay_activity"]["total_activities_cost"],
        "food_cost": stay_res["stay_activity"]["total_food_cost"],
        "budget_max": 3000.0,
        "currency": "USD",
    }).json()

    itinerary_payload = {
        "preferences": {
            "origin": "New Delhi, India",
            "destinations": ["Kyoto, Japan"],
            "start_date": start_str,
            "end_date": end_str,
            "budget_max": 3000,
            "currency": "USD",
            "travelers": 2,
            "travel_style": "cultural",
            "preferred_transport": "flight",
            "interests": ["temples"],
        },
        "destination": "Kyoto, Japan",
        "transport": trans_res["transport"],
        "stay_activity": stay_res["stay_activity"],
        "budget": budget_res,
        "weather": stay_res.get("weather"),
        "route_estimate": trans_res.get("route_estimate"),
        "rag_sources": stay_res.get("rag_sources", []),
        "destination_guidance": stay_res.get("destination_guidance", []),
    }

    res = client.post("/api/trips/stages/itinerary", json=itinerary_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["trip_id"].startswith("trip_")
    assert len(data["itinerary"]) == 5
    assert data["destinations"] == ["Kyoto, Japan"]

    # Verify persisted in database
    get_res = client.get(f"/api/trips/{data['trip_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["trip_id"] == data["trip_id"]
