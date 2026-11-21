"""Fetch rides from intervals.icu and convert them to Journal rows."""

import re
from datetime import date, timedelta

import requests

API_URL = "https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
DATE_PREFIX = re.compile(r"^\d{8}[_\-\s]*")
MAX_ZONE = 5  # the Calendrier legend stops at Z5


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


def dominant_zone(activity):
    """1-based HR zone where the ride spent the most time, capped at
    MAX_ZONE; None without heart rate data.

    Uses the athlete's own intervals.icu zones (icu_hr_zone_times).
    """
    times = activity.get("icu_hr_zone_times") or []
    if not any(times):
        return None
    return min(times.index(max(times)) + 1, MAX_ZONE)


def activity_to_row(activity):
    """Convert one intervals.icu activity to a Journal row dict.

    Values are rounded like manual entries: whole km, metres, bpm and
    minutes, speed to one decimal. zone is the dominant HR zone.
    type and comment are left out.
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
        "zone": dominant_zone(activity),
        "moy": _rounded(speed * 3.6 if speed else None, 1),
        "fc": _rounded(activity.get("average_heartrate")),
    }


def rides_to_rows(activities):
    """Keep rides only and return their Journal rows, oldest first."""
    rows = [activity_to_row(a) for a in activities if is_ride(a)]
    return sorted(rows, key=lambda row: row["date"])


def weekly_km(rows, last_monday, weeks=52):
    """Return [(monday, km)] for the `weeks` weeks ending with the week
    starting on last_monday, oldest first; weeks without rides get 0 km.

    rows are Journal rows from rides_to_rows (keys date and km).
    """
    mondays = [
        last_monday - timedelta(weeks=n) for n in reversed(range(weeks))
    ]
    totals = dict.fromkeys(mondays, 0)
    for row in rows:
        monday = row["date"] - timedelta(days=row["date"].weekday())
        if monday in totals:
            totals[monday] += row["km"]
    return list(totals.items())
