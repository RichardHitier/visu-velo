import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from odf.namespaces import OFFICENS, TABLENS
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableCell, TableRow
from odf.text import P

from download_intervals import update_summaries
from velo_tools.calendrier import (
    _auto_styles,
    _rows,
    _style_colors,
    read_legend,
    ride_colors,
    update_calendar,
)
from velo_tools.journal import _cell_at, _table, read_rides
from velo_tools.progressions import (
    format_distance,
    format_duration,
    longest_rides,
    update_progressions,
)

FIXTURE = (
    Path(__file__).parent / "fixtures" / "intervals" / "journal_26-27.ods"
)
NOV_1_ROW = 10  # Calendrier row of Nov 1 (0-based)
NOV_DAY_COL = 6  # column G
KM_COL = NOV_DAY_COL + 3
TIME_COL = NOV_DAY_COL + 4


def ride(day, km, minutes, zone=None, ride_type=""):
    return {
        "date": day,
        "type": ride_type,
        "km": km,
        "temps": timedelta(minutes=minutes),
        "zone": zone,
    }


@pytest.fixture
def doc():
    return load(str(FIXTURE))


def nov_cell(doc, day, col):
    rows = _rows(_table(doc, "Calendrier"))
    return _cell_at(rows[NOV_1_ROW + day - 1], col)


def cell_colors(doc, cell):
    style = _auto_styles(doc)[cell.getAttrNS(TABLENS, "style-name")]
    return _style_colors(style)


# --- Journal -------------------------------------------------------------


def test_read_rides_from_journal(doc):
    assert read_rides(doc) == [
        ride(date(2026, 11, 8), 26, 78, zone=2, ride_type="foncier"),
        ride(date(2026, 11, 10), 10, 31, zone=3, ride_type="tempo"),
    ]


# --- Calendrier ----------------------------------------------------------


def test_read_legend(doc):
    legend = read_legend(doc, _table(doc, "Calendrier"))
    assert {k: bg for k, (bg, _) in legend.items()} == {
        1: "#dee6ef",
        2: "#ffffd7",
        3: "#ffd428",
        4: "#ff972f",
        5: "#f10d0c",
        "affutage": "#3465a4",
        "specifique": "#afd095",
        "course": "#127622",
    }


@pytest.mark.parametrize(
    "zone, ride_type, expected",
    [
        (3, "tempo", "#ffd428"),
        (2, "", "#ffffd7"),
        (2, "Spécifique", "#afd095"),  # a special type wins over the zone
        (1, "course", "#127622"),
        (None, "foncier", None),
    ],
)
def test_ride_colors(doc, zone, ride_type, expected):
    legend = read_legend(doc, _table(doc, "Calendrier"))
    colors = ride_colors(
        ride(date(2026, 11, 8), 20, 60, zone, ride_type), legend
    )
    assert (colors[0] if colors else None) == expected


def test_update_calendar_writes_km_colors_and_week_times(doc):
    rides = read_rides(doc) + [
        ride(date(2026, 11, 10), 5, 20, zone=1),  # 2nd ride, shorter
    ]
    assert update_calendar(doc, rides) == (2, 2)

    nov_8 = nov_cell(doc, 8, KM_COL)
    assert nov_8.getAttrNS(OFFICENS, "value") == "26"
    assert cell_colors(doc, nov_8)[0] == "#ffffd7"  # Z2
    nov_10 = nov_cell(doc, 10, KM_COL)
    assert nov_10.getAttrNS(OFFICENS, "value") == "15"  # 10 + 5
    assert cell_colors(doc, nov_10)[0] == "#ffd428"  # longest ride: Z3

    # Merged week cells start on Mondays: Nov 2 and Nov 9
    week_45 = nov_cell(doc, 2, TIME_COL)
    assert week_45.getAttrNS(OFFICENS, "time-value") == "PT01H18M00S"
    week_46 = nov_cell(doc, 9, TIME_COL)
    assert week_46.getAttrNS(OFFICENS, "time-value") == "PT00H51M00S"


def test_update_calendar_leaves_days_without_rides(doc):
    before = nov_cell(doc, 16, TIME_COL).getAttrNS(OFFICENS, "time-value")
    update_calendar(doc, read_rides(doc))
    after = nov_cell(doc, 16, TIME_COL).getAttrNS(OFFICENS, "time-value")
    assert after == before


def test_update_calendar_keeps_dates_drops_sums(doc):
    update_calendar(doc, read_rides(doc))
    header = _rows(_table(doc, "Calendrier"))[8]
    month = _cell_at(header, NOV_DAY_COL)
    assert month.getAttrNS(OFFICENS, "date-value").startswith("2026-11-01")
    for row in _table(doc, "Calendrier").getElementsByType(TableRow):
        for cell in row.childNodes:
            if "SUM" in (cell.getAttrNS(TABLENS, "formula") or ""):
                assert cell.getAttrNS(OFFICENS, "value") is None


@pytest.fixture
def season(tmp_path):
    path = tmp_path / "ProgrammeCyclo_26-27.ods"
    shutil.copy(FIXTURE, path)
    return path


def test_update_calendar_twice_reuses_styles(season):
    doc = load(str(season))
    update_calendar(doc, read_rides(doc))
    doc.save(str(season))
    styles = set(_auto_styles(load(str(season))))
    doc = load(str(season))
    assert update_calendar(doc, read_rides(doc)) == (2, 2)
    doc.save(str(season))
    assert set(_auto_styles(load(str(season)))) == styles


# --- Progressions --------------------------------------------------------


@pytest.mark.parametrize(
    "minutes, expected", [(78, "1h18"), (40, "0h40"), (154, "2h34")]
)
def test_format_duration(minutes, expected):
    assert format_duration(timedelta(minutes=minutes)) == expected


@pytest.mark.parametrize("km, expected", [(26, "26,0 km"), (51.4, "51,4 km")])
def test_format_distance(km, expected):
    assert format_distance(km) == expected


def test_longest_rides_by_iso_week():
    short = ride(date(2026, 11, 10), 10, 31)
    long = ride(date(2026, 11, 15), 16, 40)  # same week 46
    other = ride(date(2026, 11, 8), 26, 78)  # week 45
    assert longest_rides([short, long, other]) == {46: long, 45: other}


def _cell(value=None):
    if value is None:
        return TableCell()
    if isinstance(value, int):
        cell = TableCell(valuetype="float", value=value)
    else:
        cell = TableCell(valuetype="string")
    cell.addElement(P(text=str(value)))
    return cell


def progressions_doc():
    doc = OpenDocumentSpreadsheet()
    table = Table(name="Progressions")
    for values in [
        [None, "Semaine ISO", "Dates", "Durée cible", "Distance cible"],
        [None, "---:", "---", "---:", "---:"],
        [None, 45, "2–8 nov.", "1h19", "26,4 km"],
        [None, 47, "16–22 nov.", "1h27", "29,1 km"],
    ]:
        row = TableRow()
        for value in values:
            row.addElement(_cell(value))
        row.addElement(TableCell(numbercolumnsrepeated=2))
        table.addElement(row)
    doc.spreadsheet.addElement(table)
    return doc


def test_update_progressions_fills_listed_weeks_only():
    doc = progressions_doc()
    rides = [
        ride(date(2026, 11, 8), 26, 78),  # week 45
        ride(date(2026, 11, 10), 10, 31),  # week 46: not listed
    ]
    assert update_progressions(doc, rides) == [45]
    rows = list(_table(doc, "Progressions").getElementsByType(TableRow))
    assert [str(_cell_at(rows[2], c)) for c in (5, 6)] == ["1h18", "26,0 km"]
    assert [str(_cell_at(rows[3], c)) for c in (5, 6)] == ["", ""]


# --- Both sheets from the file ------------------------------------------


def test_update_summaries_saves_calendar(season, tmp_path):
    doc = load(str(season))
    doc.spreadsheet.addElement(Table(name="Progressions"))
    doc.save(str(season))
    output = tmp_path / "out.ods"
    assert update_summaries(season, output) == (2, 2, [])
    saved = load(str(output))
    assert nov_cell(saved, 8, KM_COL).getAttrNS(OFFICENS, "value") == "26"
