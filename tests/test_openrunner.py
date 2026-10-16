from pathlib import Path

import pytest

from velo_tools.openrunner import load_route_summary, load_routes
from web import create_app

FIXTURES = Path(__file__).parent / "fixtures" / "openrunner"


def test_summary_uses_manifest_date():
    row = {"date": "11.10 2024"}
    route = load_route_summary(FIXTURES / "18107319.json", row)
    assert route["id"] == 18107319
    assert route["name"] == "st sernin"
    assert route["activity"] == "CYCLING"
    assert route["distance_km"] == 26.7
    assert route["dplus"] == 368
    assert route["start"] == "Limoux"
    assert route["date"] == "2024-10-11"
    assert route["polyline"] == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    assert route["passes"] == [
        {"name": "Col du Villa", "altitude": 470, "km": 14.8}
    ]


def test_summary_falls_back_on_created_at_and_missing_fields():
    route = load_route_summary(FIXTURES / "24998312.json")
    assert route["date"] == "2026-08-22"
    assert route["dplus"] is None
    assert route["start"] is None
    assert route["passes"] == []


def test_load_routes_joins_manifest_and_sorts_by_date():
    routes = load_routes(FIXTURES)
    assert [r["id"] for r in routes] == [24998312, 18107319]
    assert routes[1]["date"] == "2024-10-11"


@pytest.fixture
def client():
    app = create_app()
    app.config["OPENRUNNER_DIR"] = FIXTURES
    return app.test_client()


def test_api_routes(client):
    response = client.get("/api/routes")
    assert response.status_code == 200
    assert [r["id"] for r in response.get_json()] == [24998312, 18107319]


def test_parcours_page(client):
    response = client.get("/parcours")
    assert response.status_code == 200
    assert b'id="map"' in response.data
