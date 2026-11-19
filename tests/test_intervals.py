import shutil
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from odf.namespaces import OFFICENS, TABLENS
from odf.opendocument import load

from download_intervals import season_bounds
from velo_tools import intervals
from velo_tools.intervals import (
    activity_to_row,
    clean_name,
    dominant_zone,
    rides_to_rows,
)
from velo_tools.journal import (
    _cell_at,
    _journal_table,
    _ride_rows,
    append_rides,
    journal_dates,
)

FIXTURE = (
    Path(__file__).parent / "fixtures" / "intervals" / "journal_26-27.ods"
)

MALVIES = {
    "start_date_local": "2026-11-15T19:14:44",
    "type": "Ride",
    "name": "20261115Malvies",
    "distance": 15897.54,
    "moving_time": 2409,
    "total_elevation_gain": 56.0,
    "average_speed": 6.591,
    "average_heartrate": 134,
    "icu_hr_zone_times": [559, 1108, 647, 95, 0, 0, 0],
}


@pytest.mark.parametrize(
    "name, expected",
    [
        ("20261115Malvies", "Malvies"),
        ("20261108_StPolycarpe", "StPolycarpe"),
        ("20261110 - Al Bosc", "Al Bosc"),
        ("Sortie sans date", "Sortie sans date"),
        (None, ""),
    ],
)
def test_clean_name(name, expected):
    assert clean_name(name) == expected


def test_activity_to_row_rounds_like_manual_entries():
    assert activity_to_row(MALVIES) == {
        "date": date(2026, 11, 15),
        "destination": "Malvies",
        "km": 16,
        "temps": timedelta(minutes=40),
        "elev": 56,
        "zone": 2,
        "moy": 23.7,
        "fc": 134,
    }


def test_activity_to_row_keeps_missing_hr_and_speed_empty():
    row = activity_to_row(
        {**MALVIES, "average_heartrate": None, "average_speed": None}
    )
    assert row["fc"] is None
    assert row["moy"] is None


@pytest.mark.parametrize(
    "times, expected",
    [
        ([136, 1225, 2305, 1023, 38, 0, 0], 3),
        ([559, 1108, 647, 95, 0, 0, 0], 2),
        ([0, 0, 0, 0, 0, 10, 600], 5),  # capped at Z5
        ([0, 0, 0, 0, 0, 0, 0], None),
        (None, None),
    ],
)
def test_dominant_zone(times, expected):
    assert dominant_zone({"icu_hr_zone_times": times}) == expected


def test_rides_to_rows_keeps_rides_sorted_oldest_first():
    later = {
        **MALVIES,
        "start_date_local": "2026-11-20T10:00:00",
        "type": "GravelRide",
    }
    run = {**MALVIES, "type": "Run"}
    rows = rides_to_rows([later, run, MALVIES])
    assert [r["date"] for r in rows] == [
        date(2026, 11, 15),
        date(2026, 11, 20),
    ]


def test_fetch_activities_sends_auth_and_dates(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [MALVIES]

    def fake_get(url, auth, params, timeout):
        calls.update(url=url, auth=auth, params=params)
        return FakeResponse()

    monkeypatch.setattr(intervals.requests, "get", fake_get)
    result = intervals.fetch_activities(
        "i42", "secret", date(2026, 11, 1), date(2026, 11, 17)
    )
    assert result == [MALVIES]
    assert calls == {
        "url": "https://intervals.icu/api/v1/athlete/i42/activities",
        "auth": ("API_KEY", "secret"),
        "params": {"oldest": "2026-11-01", "newest": "2026-11-17"},
    }


def test_season_bounds_from_file_name():
    assert season_bounds(
        "ProgrammeCyclo_26-27.ods", today=date(2026, 11, 17)
    ) == (
        date(2026, 11, 1),
        date(2026, 11, 17),
    )
    assert season_bounds("ProgrammeCyclo_26-27.ods", today=date(2028, 1, 1))[
        1
    ] == date(2027, 10, 31)


def test_journal_dates_reads_existing_rides():
    assert journal_dates(FIXTURE) == {date(2026, 11, 8), date(2026, 11, 10)}


@pytest.fixture
def journal(tmp_path):
    path = tmp_path / "ProgrammeCyclo_26-27.ods"
    shutil.copy(FIXTURE, path)
    return path


def test_append_rides_fills_first_empty_row(journal):
    filled = append_rides(journal, [activity_to_row(MALVIES)])
    assert filled == [3]
    assert journal_dates(journal) == {
        date(2026, 11, 8),
        date(2026, 11, 10),
        date(2026, 11, 15),
    }
    df = pd.read_excel(journal, sheet_name="Journal", header=4)
    row = df[df["n."] == 3].iloc[0]
    assert row["destination"] == "Malvies"
    assert (row["km"], row["elev"], row["moy"], row["fc"]) == (
        16,
        56,
        23.7,
        134,
    )
    assert str(row["temps"]) == "00:40:00"
    assert pd.isna(row["type"])
    assert float(row["zone"]) == 2  # pandas turns the text "2" into 2.0
    # Existing rides untouched
    assert df[df["n."] == 1].iloc[0]["destination"] == "St Polycarpe"


def test_append_rides_keeps_styles_and_formula(journal):
    def third_row_cells(path):
        rows = list(_ride_rows(_journal_table(load(str(path)))))
        return [_cell_at(rows[2], col) for col in range(2, 12)]

    styles_before = [
        c.getAttrNS(TABLENS, "style-name") for c in third_row_cells(journal)
    ]
    append_rides(journal, [activity_to_row(MALVIES)])
    cells = third_row_cells(journal)
    assert [c.getAttrNS(TABLENS, "style-name") for c in cells] == styles_before
    w_cell = cells[0]
    assert w_cell.getAttrNS(TABLENS, "formula") == 'of:=IF([.D8]="";"";[.D8])'
    assert w_cell.getAttrNS(OFFICENS, "date-value") == "2026-11-15"


def test_append_rides_drops_stale_totals(journal):
    def total_km_cell(path):
        table = _journal_table(load(str(path)))
        first_ride = next(_ride_rows(table))
        return _cell_at(first_ride, 18)  # column S: =SUM([.S6:.S26])

    assert total_km_cell(journal).getAttrNS(OFFICENS, "value") == "36"
    append_rides(journal, [activity_to_row(MALVIES)])
    cell = total_km_cell(journal)
    assert cell.getAttrNS(TABLENS, "formula").startswith("of:=SUM")
    assert cell.getAttrNS(OFFICENS, "value") is None
    assert not cell.childNodes


def test_append_rides_refuses_overflow(journal):
    with pytest.raises(ValueError, match="empty Journal rows"):
        append_rides(journal, [activity_to_row(MALVIES)] * 1000)
