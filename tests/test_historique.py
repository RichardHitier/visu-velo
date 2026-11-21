from datetime import date, timedelta

import pandas as pd
import pytest
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableCell, TableRow

from velo_tools.journal import (
    _set_value,
    add_journal_sheet,
    parse_horaire,
    read_historique,
    read_rides,
)
from velo_tools.readers import ods_to_df

HEADER = [
    "date", "type", "destination", "km", "Deniv", "horaire",
    "RPE Borg", "FC Moy", "FC Max", "V Moy", "V Max",
]  # fmt: skip
LINES = [
    [date(2023, 1, 22), "vélo", "Festes", 31, 414, "1h31", "4", 150, 165,
     21.4, 55.11],
    [date(2022, 11, 27), "vélo", "Buc", 30, 426, "1h30", 5, 150, 170,
     None, None],
    [date(2023, 2, 21), "rando", "Bugarach", 3.4, 523, "1h40", "5", 150,
     160, None, None],
]  # fmt: skip


@pytest.fixture
def old_season():
    """A doc shaped like ProgrammeCyclo_22-23.ods: an Historique sheet."""
    doc = OpenDocumentSpreadsheet()
    table = Table(name="Historique")
    for values in [HEADER, *LINES]:
        row = TableRow()
        for value in values:
            cell = TableCell()
            _set_value(cell, value)
            row.addElement(cell)
        table.addElement(row)
    doc.spreadsheet.addElement(table)
    return doc


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1h30", timedelta(hours=1, minutes=30)),
        ("1h", timedelta(hours=1)),
        ("0h59", timedelta(minutes=59)),
        (" 2h05 ", timedelta(hours=2, minutes=5)),
    ],
)
def test_parse_horaire(text, expected):
    assert parse_horaire(text) == expected


@pytest.mark.parametrize("text", ["", "90", "1:30", None])
def test_parse_horaire_rejects_unreadable(text):
    with pytest.raises(ValueError):
        parse_horaire(text)


def test_read_historique_keeps_bike_rides_oldest_first(old_season):
    rides = read_historique(old_season)
    assert [r["destination"] for r in rides] == ["Buc", "Festes"]
    assert rides[1] == {
        "date": date(2023, 1, 22),
        "destination": "Festes",
        "km": 31,
        "temps": timedelta(hours=1, minutes=31),
        "elev": 414,
        "zone": None,
        "moy": 21.4,
        "fc": 150,
        "comment": "RPE 4, FC max 165, V max 55.11",
    }
    assert rides[0]["moy"] is None
    assert rides[0]["comment"] == "RPE 5, FC max 170"


def test_add_journal_sheet_is_read_like_other_seasons(old_season, tmp_path):
    add_journal_sheet(old_season, read_historique(old_season))
    path = tmp_path / "ProgrammeCyclo_22-23.ods"
    old_season.save(str(path))

    rides = read_rides(load(str(path)))
    assert [(r["date"], r["km"], r["temps"]) for r in rides] == [
        (date(2022, 11, 27), 30, timedelta(hours=1, minutes=30)),
        (date(2023, 1, 22), 31, timedelta(hours=1, minutes=31)),
    ]
    journal = pd.read_excel(path, sheet_name="Journal", header=4)
    assert list(journal.columns[:13]) == [
        "Bloc", "n.", "w", "date", "destination", "type", "km",
        "temps", "elev", "zone", "moy", "fc", "Comment",
    ]  # fmt: skip
    assert list(journal["n."]) == [1, 2]
    df = ods_to_df(path)
    assert df["km"].sum() == 61
    assert df.loc["2023-01-22", "elev"] == 414


def test_add_journal_sheet_refuses_a_second_journal(old_season):
    add_journal_sheet(old_season, [])
    with pytest.raises(ValueError, match="already has"):
        add_journal_sheet(old_season, [])
