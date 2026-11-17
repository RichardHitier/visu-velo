"""Fetch rides from intervals.icu and convert them to Journal rows."""

import re
from datetime import date, timedelta

import requests

API_URL = "https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
DATE_PREFIX = re.compile(r"^\d{8}[_\-\s]*")


def fetch_activities(athlete_id, api_key, oldest, newest):
    """Return intervals.icu activities between two dates (inclusive)."""
    response = requests.get(
        API_URL.format(athlete_id=athlete_id),
        auth=("API_KEY", api_key),
        params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def is_ride(activity):
    """True for any cycling activity (Ride, VirtualRide, GravelRide...)."""
    return "Ride" in (activity.get("type") or "")


def clean_name(name):
    """Strip a leading yyyymmdd date and its separator from a name."""
    return DATE_PREFIX.sub("", name or "").strip()


def _rounded(value, digits=None):
    """Round value, keeping None for missing data."""
    return None if value is None else round(value, digits)


def activity_to_row(activity):
    """Convert one intervals.icu activity to a Journal row dict.

    Values are rounded like manual entries: whole km, metres, bpm and
    minutes, speed to one decimal. type, zone and comment are left out.
    """
    speed = activity.get("average_speed")
    return {
        "date": date.fromisoformat(activity["start_date_local"][:10]),
        "destination": clean_name(activity.get("name")),
        "km": _rounded((activity.get("distance") or 0) / 1000),
        "temps": timedelta(
            minutes=round((activity.get("moving_time") or 0) / 60)
        ),
        "elev": _rounded(activity.get("total_elevation_gain")),
        "moy": _rounded(speed * 3.6 if speed else None, 1),
        "fc": _rounded(activity.get("average_heartrate")),
    }


def rides_to_rows(activities):
    """Keep rides only and return their Journal rows, oldest first."""
    rows = [activity_to_row(a) for a in activities if is_ride(a)]
    return sorted(rows, key=lambda row: row["date"])
