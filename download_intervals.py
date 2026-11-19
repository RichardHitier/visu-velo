#!/usr/bin/env python3
"""Fill a ProgrammeCyclo ODS from intervals.icu rides.

Usage:
    python download_intervals.py ProgrammeCyclo_26-27.ods [--dry-run]
    python download_intervals.py ProgrammeCyclo_26-27.ods --output OUT.ods

Needs INTERVALS_API_KEY and INTERVALS_ATHLETE_ID in the environment.
Rides are fetched over the season named in the file (26-27: 2026-11-01 to
2027-10-31); a ride is new when its date is not already in the Journal.
zone is guessed (dominant HR zone); type and comment are left for manual
entry.

Then the Calendrier and Progressions sheets are rewritten from the whole
Journal, so manual corrections there (zone, type, km...) are taken into
account on each run.
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

from odf.opendocument import load

from velo_tools.calendrier import update_calendar
from velo_tools.intervals import fetch_activities, rides_to_rows
from velo_tools.journal import append_rides, journal_dates, read_rides
from velo_tools.progressions import update_progressions


def season_bounds(path, today=None):
    """Return (Nov 1, min(Oct 31, today)) for a 'ProgrammeCyclo_YY-YY' file."""
    match = re.search(r"(\d{2})-(\d{2})", Path(path).stem)
    if not match:
        raise ValueError(f"No season 'YY-YY' in file name {path}")
    first = 2000 + int(match.group(1))
    end = date(first + 1, 10, 31)
    return date(first, 11, 1), min(end, today or date.today())


def update_summaries(path, output=None):
    """Rewrite Calendrier and Progressions of path from its Journal."""
    doc = load(str(path))
    rides = read_rides(doc)
    days, weeks = update_calendar(doc, rides)
    long_weeks = update_progressions(doc, rides)
    doc.save(str(output or path))
    return days, weeks, long_weeks


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
            f"  {ride['moy']} km/h  {ride['fc']} bpm  Z{ride['zone']}"
        )
    if not rides:
        print("No new ride.")
    if args.dry_run:
        return
    target = args.output or args.ods
    source = args.ods
    if rides:
        filled = append_rides(args.ods, rides, args.output)
        numbers = ", ".join(map(str, filled))
        print(f"Wrote Journal rows n. {numbers} in {target}")
        source = target
    days, weeks, long_weeks = update_summaries(source, target)
    print(f"Calendrier: {days} days, {weeks} week times")
    print(f"Progressions: weeks {', '.join(map(str, long_weeks)) or 'none'}")


if __name__ == "__main__":
    main()
