#!/usr/bin/env python3
"""Fill the Journal sheet of a ProgrammeCyclo ODS with intervals.icu rides.

Usage:
    python download_intervals.py ProgrammeCyclo_26-27.ods [--dry-run]
    python download_intervals.py ProgrammeCyclo_26-27.ods --output OUT.ods

Needs INTERVALS_API_KEY and INTERVALS_ATHLETE_ID in the environment.
Rides are fetched over the season named in the file (26-27: 2026-11-01 to
2027-10-31); a ride is new when its date is not already in the Journal.
type, zone and comment are left for manual entry.
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

from velo_tools.intervals import fetch_activities, rides_to_rows
from velo_tools.journal import append_rides, journal_dates


def season_bounds(path, today=None):
    """Return (Nov 1, min(Oct 31, today)) for a 'ProgrammeCyclo_YY-YY' file."""
    match = re.search(r"(\d{2})-(\d{2})", Path(path).stem)
    if not match:
        raise ValueError(f"No season 'YY-YY' in file name {path}")
    first = 2000 + int(match.group(1))
    end = date(first + 1, 10, 31)
    return date(first, 11, 1), min(end, today or date.today())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ods", type=Path)
    parser.add_argument(
        "--output", type=Path, help="write here instead of in place"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="list new rides only"
    )
    args = parser.parse_args()

    try:
        api_key = os.environ["INTERVALS_API_KEY"]
        athlete_id = os.environ["INTERVALS_ATHLETE_ID"]
    except KeyError as missing:
        sys.exit(f"Missing environment variable {missing}")

    oldest, newest = season_bounds(args.ods)
    known = journal_dates(args.ods)
    rides = [
        ride
        for ride in rides_to_rows(
            fetch_activities(athlete_id, api_key, oldest, newest)
        )
        if ride["date"] not in known
    ]
    for ride in rides:
        print(
            f"{ride['date']:%d/%m/%y}  {ride['destination']:<20}"
            f" {ride['km']:>4} km  {ride['temps']}  {ride['elev']} m+"
            f"  {ride['moy']} km/h  {ride['fc']} bpm"
        )
    if not rides:
        print("No new ride.")
        return
    if args.dry_run:
        return
    filled = append_rides(args.ods, rides, args.output)
    numbers = ", ".join(map(str, filled))
    print(f"Wrote rows n. {numbers} in {args.output or args.ods}")


if __name__ == "__main__":
    main()
