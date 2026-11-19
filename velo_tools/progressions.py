"""Update the 'Progressions' sheet of a ProgrammeCyclo ODS from Journal rides.

The sheet has one row per ISO week holding a long ride (column B: week
number). For each listed week, 'Durée réelle' and 'Distance réelle' get the
time and distance of the week's longest ride (by distance). Weeks are
matched on their number only: within a Nov 1 -> Oct 31 season an ISO week
number is never used twice.
"""

from odf.namespaces import OFFICENS
from odf.table import TableRow

from velo_tools.journal import _cell_at, _repeat, _set_value, _table

SHEET = "Progressions"
WEEK_COL = 1
DURATION_COL = 5
DISTANCE_COL = 6


def format_duration(duration):
    """timedelta -> '1h32', like the 'Durée cible' column."""
    minutes = round(duration.total_seconds() / 60)
    return f"{minutes // 60}h{minutes % 60:02d}"


def format_distance(km):
    """26 -> '26,0 km', like the 'Distance cible' column."""
    return f"{km:.1f} km".replace(".", ",")


def longest_rides(rides):
    """Return {ISO week number: longest ride of that week}."""
    longest = {}
    for ride in rides:
        week = ride["date"].isocalendar().week
        if week not in longest or ride["km"] > longest[week]["km"]:
            longest[week] = ride
    return longest


def update_progressions(doc, rides):
    """Write the long rides (dicts from journal.read_rides) into the
    Progressions sheet of doc. Returns the week numbers written.
    """
    longest = longest_rides(rides)
    written = []
    for row in _table(doc, SHEET).getElementsByType(TableRow):
        if _repeat(row, "number-rows-repeated") > 1:
            continue
        try:
            week_cell = _cell_at(row, WEEK_COL)
        except IndexError:
            continue
        if week_cell.getAttrNS(OFFICENS, "value-type") != "float":
            continue
        week = int(float(week_cell.getAttrNS(OFFICENS, "value")))
        ride = longest.get(week)
        if ride is None:
            continue
        _set_value(_cell_at(row, DURATION_COL), format_duration(ride["temps"]))
        _set_value(_cell_at(row, DISTANCE_COL), format_distance(ride["km"]))
        written.append(week)
    return written
