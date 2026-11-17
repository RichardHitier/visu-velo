"""Read and fill the 'Journal' sheet of a ProgrammeCyclo ODS, keeping styles.

Ride rows are pre-numbered (column 'n.') and pre-styled in the template:
filling a ride means writing values into the cells of the first row whose
'date' cell is empty. Formulas are kept: column 'w' gets its new cached
result, the other ones (totals) lose theirs so LibreOffice recomputes them.
"""

from datetime import date, timedelta

from odf.element import Element
from odf.namespaces import OFFICENS, TABLENS
from odf.opendocument import load
from odf.table import Table, TableRow
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
    "moy": 10,
    "fc": 11,
}
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


def _journal_table(doc):
    for table in doc.spreadsheet.getElementsByType(Table):
        if table.getAttribute("name") == SHEET:
            return table
    raise ValueError(f"No '{SHEET}' sheet in document")


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
            _set_value(_cell_at(row, col), value)
        num = _cell_at(row, COLUMNS["num"]).getAttrNS(OFFICENS, "value")
        filled.append(int(float(num)))
    _drop_cached_results(table)
    doc.save(str(output or path))
    return filled


def _drop_cached_results(table):
    """Clear the cached result of the table's formulas, except column 'w'.

    LibreOffice does not recalculate a file it did not save itself, so stale
    totals would stay; a formula without a cached result is computed on load.
    'w' results are written by append_rides and stay readable by pandas.
    """
    for row in table.getElementsByType(TableRow):
        col = 0
        for cell in row.childNodes:
            if cell.getAttrNS(TABLENS, "formula") and col != COLUMNS["w"]:
                _clear_value(cell)
            col += _repeat(cell, "number-columns-repeated")
