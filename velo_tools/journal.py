"""Read and fill the 'Journal' sheet of a ProgrammeCyclo ODS, keeping styles.

Ride rows are pre-numbered (column 'n.') and pre-styled in the template:
filling a ride means writing values into the cells of the first row whose
'date' cell is empty. Formulas are kept: column 'w' gets its new cached
result, the other ones (totals) lose theirs so LibreOffice recomputes them.
"""

import re
from datetime import date, timedelta

from odf.element import Element
from odf.namespaces import OFFICENS, TABLENS
from odf.opendocument import load
from odf.number import DateStyle, Day, Hours, Minutes, Month, TimeStyle
from odf.number import Text as NumberText
from odf.number import Year
from odf.style import Style, TextProperties
from odf.table import Table, TableCell, TableRow
from odf.text import P

SHEET = "Journal"
COLUMNS = {
    "num": 1,
    "w": 2,
    "date": 3,
    "destination": 4,
    "km": 6,
    "temps": 7,
    "elev": 8,
    "zone": 9,
    "moy": 10,
    "fc": 11,
}
TYPE_COL = 5
DURATION = re.compile(r"PT(\d+)H(\d+)M(\d+(?:\.\d+)?)S")
DIGIT = re.compile(r"\d")
HORAIRE = re.compile(r"^\s*(\d+)\s*h\s*(\d*)\s*$")
HISTORIQUE = "Historique"
JOURNAL_HEADER = (
    "Bloc",
    "n.",
    "w",
    "date",
    "destination",
    "type",
    "km",
    "temps",
    "elev",
    "zone",
    "moy",
    "fc",
    "Comment",
)
COMMENT_COL = 12
HEADER_STYLE, DATE_STYLE, TIME_STYLE = "JrnHeader", "JrnDate", "JrnTime"
CALCEXTNS = (
    "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0"
)
VALUE_ATTRS = (
    "value-type",
    "value",
    "date-value",
    "time-value",
    "string-value",
)


def _table(doc, name):
    for table in doc.spreadsheet.getElementsByType(Table):
        if table.getAttribute("name") == name:
            return table
    raise ValueError(f"No '{name}' sheet in document")


def _journal_table(doc):
    return _table(doc, SHEET)


def _repeat(element, attr):
    return int(element.getAttrNS(TABLENS, attr) or 1)


def _cell_at(row, col):
    """Return the cell at column col, splitting a repeated cell if needed."""
    start = 0
    for cell in list(row.childNodes):
        repeat = _repeat(cell, "number-columns-repeated")
        if start + repeat > col:
            if repeat == 1:
                return cell
            if cell.childNodes:
                raise ValueError(
                    "Cannot split a repeated cell holding content"
                )
            return _split_cell(row, cell, col - start, repeat)
        start += repeat
    raise IndexError(f"Row has no column {col}")


def _split_cell(row, cell, offset, repeat):
    """Split a repeated empty cell into before / target / after cells."""
    pieces = [n for n in (offset, 1, repeat - offset - 1) if n]
    clones = []
    for count in pieces:
        clone = Element(qname=cell.qname, check_grammar=False)
        clone.attributes = dict(cell.attributes)
        clone.attributes.pop((TABLENS, "number-columns-repeated"), None)
        if count > 1:
            clone.attributes[(TABLENS, "number-columns-repeated")] = str(count)
        row.insertBefore(clone, cell)
        clones.append(clone)
    row.removeChild(cell)
    return clones[1] if offset else clones[0]


def _ride_rows(table):
    """Yield the pre-numbered ride rows (a float in column 'n.')."""
    for row in table.getElementsByType(TableRow):
        if _repeat(row, "number-rows-repeated") > 1:
            continue
        try:
            num = _cell_at(row, COLUMNS["num"])
        except IndexError:
            continue
        if num.getAttrNS(OFFICENS, "value-type") == "float":
            yield row


def _cell_date(cell):
    value = cell.getAttrNS(OFFICENS, "date-value")
    return date.fromisoformat(value[:10]) if value else None


def _cell_number(cell):
    value = cell.getAttrNS(OFFICENS, "value")
    return float(value) if value else None


def _cell_duration(cell):
    match = DURATION.match(cell.getAttrNS(OFFICENS, "time-value") or "")
    if not match:
        return timedelta(0)
    hours, minutes, seconds = match.groups()
    return timedelta(
        hours=int(hours), minutes=int(minutes), seconds=float(seconds)
    )


def _cell_zone(cell):
    """Zone typed as text ('3', 'Z3') or number; None when empty."""
    match = DIGIT.search(str(cell))
    return int(match.group()) if match else None


def _clear_value(cell):
    for child in list(cell.childNodes):
        cell.removeChild(child)
    for attr in VALUE_ATTRS:
        cell.attributes.pop((OFFICENS, attr), None)
    cell.attributes.pop((CALCEXTNS, "value-type"), None)


def _set_value(cell, value):
    """Write a str, number, date or timedelta into cell, keeping its style."""
    _clear_value(cell)
    if value is None:
        return
    if isinstance(value, str):
        cell.setAttrNS(OFFICENS, "value-type", "string")
        text = value
    elif isinstance(value, date):
        cell.setAttrNS(OFFICENS, "value-type", "date")
        cell.setAttrNS(OFFICENS, "date-value", value.isoformat())
        text = value.strftime("%d/%m/%y")
    elif isinstance(value, timedelta):
        minutes = round(value.total_seconds() / 60)
        cell.setAttrNS(OFFICENS, "value-type", "time")
        cell.setAttrNS(
            OFFICENS,
            "time-value",
            f"PT{minutes // 60:02d}H{minutes % 60:02d}M00S",
        )
        text = f"{minutes // 60:02d}:{minutes % 60:02d}:00"
    else:
        cell.setAttrNS(OFFICENS, "value-type", "float")
        cell.setAttrNS(OFFICENS, "value", str(value))
        text = str(value)
    cell.addElement(P(text=text))


def journal_dates(path):
    """Return the set of ride dates already in the Journal."""
    table = _journal_table(load(str(path)))
    dates = (
        _cell_date(_cell_at(row, COLUMNS["date"])) for row in _ride_rows(table)
    )
    return {d for d in dates if d}


def read_rides(doc):
    """Return the Journal rides of a loaded doc, as dicts with
    date, type (lowercase, '' when empty), km, temps and zone (or None).
    """
    rides = []
    for row in _ride_rows(_journal_table(doc)):
        day = _cell_date(_cell_at(row, COLUMNS["date"]))
        if not day:
            continue
        rides.append(
            {
                "date": day,
                "type": str(_cell_at(row, TYPE_COL)).strip().lower(),
                "km": _cell_number(_cell_at(row, COLUMNS["km"])) or 0,
                "temps": _cell_duration(_cell_at(row, COLUMNS["temps"])),
                "zone": _cell_zone(_cell_at(row, COLUMNS["zone"])),
            }
        )
    return rides


def append_rides(path, rides, output=None):
    """Write rides (dicts from intervals.activity_to_row) into the first
    empty Journal rows of path; save to output (default: path).

    Returns the 'n.' numbers of the filled rows.
    """
    doc = load(str(path))
    table = _journal_table(doc)
    empty = [
        r
        for r in _ride_rows(table)
        if not _cell_date(_cell_at(r, COLUMNS["date"]))
    ]
    if len(rides) > len(empty):
        raise ValueError(
            f"{len(rides)} rides but only {len(empty)} empty Journal rows"
        )
    filled = []
    for row, ride in zip(empty, rides):
        for key, col in COLUMNS.items():
            if key == "num":
                continue
            value = ride["date"] if key == "w" else ride.get(key)
            if key == "zone" and value is not None:
                value = str(value)  # typed as text by hand in the Journal
            _set_value(_cell_at(row, col), value)
        num = _cell_at(row, COLUMNS["num"]).getAttrNS(OFFICENS, "value")
        filled.append(int(float(num)))
    _drop_cached_results(table, keep=lambda cell, col: col == COLUMNS["w"])
    doc.save(str(output or path))
    return filled


def _drop_cached_results(table, keep):
    """Clear the cached result of the table's formulas, except where
    keep(cell, col) is true.

    LibreOffice does not recalculate a file it did not save itself, so stale
    totals would stay; a formula without a cached result is computed on load.
    In the Journal, 'w' results are written by append_rides and stay
    readable by pandas.
    """
    for row in table.getElementsByType(TableRow):
        col = 0
        for cell in row.childNodes:
            if cell.getAttrNS(TABLENS, "formula") and not keep(cell, col):
                _clear_value(cell)
            col += _repeat(cell, "number-columns-repeated")


def parse_horaire(text):
    """Duration typed as '1h30', '1h' or '0h59' in old Historique sheets."""
    match = HORAIRE.match(text or "")
    if not match:
        raise ValueError(f"Unreadable duration {text!r}")
    hours, minutes = match.groups()
    return timedelta(hours=int(hours), minutes=int(minutes or 0))


def _cell_float(cell):
    """Number of a cell, also when typed as text ('4', '21,4')."""
    value = _cell_number(cell)
    if value is None:
        try:
            value = float(str(cell).replace(",", "."))
        except ValueError:
            return None
    return int(value) if value.is_integer() else value


def _row_texts(row):
    texts = []
    for cell in row.childNodes:
        texts += [str(cell).strip()] * _repeat(cell, "number-columns-repeated")
    return texts


def read_historique(doc):
    """Return the bike rides of an old 'Historique' sheet (22-23 season) as
    Journal row dicts (like intervals.activity_to_row, plus comment),
    oldest first. Other activities (rando...) are skipped.
    """
    rows = [
        row
        for row in _table(doc, HISTORIQUE).getElementsByType(TableRow)
        if _repeat(row, "number-rows-repeated") == 1
    ]
    header = _row_texts(rows[0])
    rides = []
    for row in rows[1:]:

        def cell(name):
            return _cell_at(row, header.index(name))

        day = _cell_date(cell("date"))
        if not day or str(cell("type")).strip().lower() != "vélo":
            continue
        notes = [
            (label, _cell_float(cell(name)))
            for label, name in (
                ("RPE", "RPE Borg"),
                ("FC max", "FC Max"),
                ("V max", "V Max"),
            )
        ]
        rides.append(
            {
                "date": day,
                "destination": str(cell("destination")).strip(),
                "km": _cell_float(cell("km")),
                "temps": parse_horaire(str(cell("horaire"))),
                "elev": _cell_float(cell("Deniv")),
                "zone": None,
                "moy": _cell_float(cell("V Moy")),
                "fc": _cell_float(cell("FC Moy")),
                "comment": ", ".join(
                    f"{label} {value}"
                    for label, value in notes
                    if value is not None
                )
                or None,
            }
        )
    return sorted(rides, key=lambda ride: ride["date"])


def _add_journal_styles(doc):
    """Bold header, dd/mm/yyyy dates and hh:mm durations."""
    date_format = DateStyle(name="JrnDateFmt")
    for part in (
        Day(style="long"),
        NumberText(text="/"),
        Month(style="long"),
        NumberText(text="/"),
        Year(style="long"),
    ):
        date_format.addElement(part)
    time_format = TimeStyle(name="JrnTimeFmt", truncateonoverflow="false")
    for part in (Hours(style="long"), NumberText(text=":"), Minutes()):
        time_format.addElement(part)
    header = Style(name=HEADER_STYLE, family="table-cell")
    header.addElement(TextProperties(fontweight="bold"))
    for element in (
        date_format,
        time_format,
        header,
        Style(
            name=DATE_STYLE, family="table-cell", datastylename="JrnDateFmt"
        ),
        Style(
            name=TIME_STYLE, family="table-cell", datastylename="JrnTimeFmt"
        ),
    ):
        doc.automaticstyles.addElement(element)


def add_journal_sheet(doc, rides):
    """Append a Journal sheet holding rides (dicts from read_historique):
    4 empty rows, the header on row 5, then one numbered row per ride,
    as read by read_rides and readers.ods_to_df.
    """
    tables = doc.spreadsheet.getElementsByType(Table)
    if any(table.getAttribute("name") == SHEET for table in tables):
        raise ValueError(f"Document already has a '{SHEET}' sheet")
    _add_journal_styles(doc)
    table = Table(name=SHEET)
    for _ in range(4):
        row = TableRow()
        row.addElement(TableCell())
        table.addElement(row)
    header = TableRow()
    for name in JOURNAL_HEADER:
        cell = TableCell(stylename=HEADER_STYLE)
        _set_value(cell, name)
        header.addElement(cell)
    table.addElement(header)
    for num, ride in enumerate(rides, start=1):
        values = [None] * len(JOURNAL_HEADER)
        for key, col in COLUMNS.items():
            values[col] = ride.get(key)
        values[COLUMNS["num"]] = num
        values[COLUMNS["w"]] = ride["date"]
        values[COMMENT_COL] = ride.get("comment")
        row = TableRow()
        for value in values:
            if isinstance(value, date):
                cell = TableCell(stylename=DATE_STYLE)
            elif isinstance(value, timedelta):
                cell = TableCell(stylename=TIME_STYLE)
            else:
                cell = TableCell()
            _set_value(cell, value)
            row.addElement(cell)
        table.addElement(row)
    doc.spreadsheet.addElement(table)
