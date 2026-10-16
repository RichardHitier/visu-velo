"""Readers for OpenRunner route exports (data/openrunner/<id>.json|.gpx)."""

import csv
import json
from datetime import datetime
from pathlib import Path


def _parse_manifest_date(value):
    """Convert an OpenRunner 'dd.mm yyyy' date to ISO 'yyyy-mm-dd', or None."""
    try:
        return datetime.strptime(value.strip(), "%d.%m %Y").date().isoformat()
    except (AttributeError, ValueError):
        return None


def load_route_summary(json_path, manifest_row=None):
    """Build a light summary dict of one route from its OpenRunner JSON.

    manifest_row is the matching routes.csv row (a dict), used for the date;
    falls back to the JSON 'created_at' when absent or unparsable.
    """
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))["data"]
    elevation = data.get("elevation") or {}
    date = _parse_manifest_date((manifest_row or {}).get("date"))
    if date is None:
        date = data["created_at"][:10]
    return {
        "id": data["id"],
        "name": data["name"],
        "activity": data["activity"]["name"],
        "distance_km": round(data["length"] / 1000, 1),
        "dplus": elevation.get("ascent"),
        "dminus": elevation.get("descent"),
        "ele_min": elevation.get("min"),
        "ele_max": elevation.get("max"),
        "loop_type": data.get("loop_type"),
        "start": (data.get("start_location") or {}).get("name"),
        "date": date,
        "polyline": data["shape"]["full_encoded"],
        "passes": [
            {
                "name": p["name"],
                "altitude": p["altitude_in_meter"],
                "km": round(p["location_in_meter"] / 1000, 1),
            }
            for p in data.get("passes") or []
        ],
    }


def read_manifest(data_dir):
    """Return routes.csv rows keyed by route id (str); empty if missing."""
    path = Path(data_dir) / "routes.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def load_routes(data_dir):
    """Load all route summaries from data_dir, most recent first."""
    manifest = read_manifest(data_dir)
    routes = [
        load_route_summary(path, manifest.get(path.stem))
        for path in Path(data_dir).glob("*.json")
    ]
    return sorted(routes, key=lambda r: r["date"], reverse=True)
