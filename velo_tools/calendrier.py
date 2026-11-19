"""Update the 'Calendrier' sheet of a ProgrammeCyclo ODS from Journal rides.

Each month is a block of columns under a header cell holding the 1st of the
month (a DATE formula): day number, weekday letter, ISO week, km, week time,
comment. Day d sits on the d-th row below the month name.

The Journal is the reference:
- the km cell of a day with rides gets the day's total and the colors of
  its longest ride, read from the legend in column A: a special type
  (Affûtage, Spécifique, COURSE) wins over the zone (Z1..Z5);
- a week-time cell (merged over the days of a week inside the month) gets
  the total time of the days it covers, when they hold a ride.
Days and weeks without rides are left as they are.
"""

import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import timedelta

from odf.element import Element
from odf.namespaces import FONS, OFFICENS, STYLENS, TABLENS
from odf.table import TableRow

from velo_tools.journal import (
    _cell_at,
    _cell_date,
    _drop_cached_results,
    _repeat,
    _set_value,
    _table,
)

SHEET = "Calendrier"
LEGEND_COL = 0
DAY_ROW_OFFSET = 1  # day d is on header row + 1 + d
KM_OFFSET = 3
TIME_OFFSET = 4
ZONE_LABEL = re.compile(r"^Z(\d)\b")
STYLE_PREFIX = "vv"
MAX_ROWS_REPEATED = 1000  # trailing filler rows are repeated ~1M times


def _normalize(text):
    """Lowercase text without accents: 'Affûtage' -> 'affutage'."""
    decomposed = unicodedata.normalize("NFKD", text.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _rows(table):
    """All rows of table by index, a repeated row appearing several times."""
    rows = []
    for row in table.getElementsByType(TableRow):
        repeat = _repeat(row, "number-rows-repeated")
        rows.extend([row] * min(repeat, MAX_ROWS_REPEATED))
    return rows


def _auto_styles(doc):
    return {
        style.getAttrNS(STYLENS, "name"): style
        for style in doc.automaticstyles.childNodes
        if style.qname[1] == "style"
    }


def _properties(style, kind):
    for child in style.childNodes:
        if child.qname[1] == kind:
            return child
    return None


def _style_colors(style):
    """(background, font color or None) of a cell style."""
    cell_props = _properties(style, "table-cell-properties")
    text_props = _properties(style, "text-properties")
    background = cell_props and cell_props.getAttrNS(FONS, "background-color")
    font = text_props and text_props.getAttrNS(FONS, "color")
    return background, font


def read_legend(doc, table):
    """Return {zone number or normalized type: (background, font color)}
    from the legend cells of column A.
    """
    styles = _auto_styles(doc)
    legend = {}
    for row in table.getElementsByType(TableRow):
        if _repeat(row, "number-rows-repeated") > 1:
            continue
        cell = _cell_at(row, LEGEND_COL)
        label = str(cell).strip()
        style = styles.get(cell.getAttrNS(TABLENS, "style-name"))
        if not label or style is None:
            continue
        background, font = _style_colors(style)
        if not background or background == "transparent":
            continue
        zone = ZONE_LABEL.match(label)
        key = int(zone.group(1)) if zone else _normalize(label).lower()
        legend[key] = (background, font)
    return legend


def ride_colors(ride, legend):
    """Colors of a ride: its type when the legend has it, else its zone."""
    ride_type = _normalize(ride["type"]).lower()
    if ride_type in legend:
        return legend[ride_type]
    return legend.get(ride["zone"])


def _clone(element):
    copy = Element(qname=element.qname, check_grammar=False)
    copy.attributes = dict(element.attributes)
    for child in element.childNodes:
        copy.appendChild(_clone(child))
    return copy


def _colored_style(doc, styles, base_name, colors):
    """Name of a copy of style base_name with the given colors, created
    in doc (and styles) the first time.
    """
    if base_name.startswith(STYLE_PREFIX + "-"):
        base_name = base_name.split("-")[1]
    background, font = colors
    name = f"{STYLE_PREFIX}-{base_name}-{background.lstrip('#')}"
    if font:
        name += f"-{font.lstrip('#')}"
    if name in styles:
        return name
    style = _clone(styles[base_name])
    style.attributes[(STYLENS, "name")] = name
    cell_props = _properties(style, "table-cell-properties")
    if cell_props is None:
        cell_props = Element(
            qname=(STYLENS, "table-cell-properties"), check_grammar=False
        )
        style.appendChild(cell_props)
    cell_props.attributes[(FONS, "background-color")] = background
    text_props = _properties(style, "text-properties")
    if font and text_props is not None:
        text_props.attributes[(FONS, "color")] = font
        text_props.attributes.pop((STYLENS, "use-window-font-color"), None)
    doc.automaticstyles.addElement(style)
    styles[name] = style
    return name


def _months(rows):
    """Yield (first day of month, header row index, day column) for each
    month block: a date cell on the 1st whose day-1 row holds 1.
    """
    for index, row in enumerate(rows):
        col = 0
        for cell in row.childNodes:
            day = _cell_date(cell)
            if day and day.day == 1:
                first_row = index + DAY_ROW_OFFSET + 1
                if first_row < len(rows):
                    first = _cell_at(rows[first_row], col)
                    if first.getAttrNS(OFFICENS, "value") == "1":
                        yield day, index, col
            col += _repeat(cell, "number-columns-repeated")


def _day_row(rows, header, col, day):
    row = rows[header + DAY_ROW_OFFSET + day.day]
    if _repeat(row, "number-rows-repeated") > 1:
        raise ValueError(f"Calendrier row of {day} is a repeated row")
    number = _cell_at(row, col).getAttrNS(OFFICENS, "value")
    if number is None or int(float(number)) != day.day:
        raise ValueError(f"Calendrier: no day {day.day} where {day} should be")
    return row


def _km_value(km):
    return int(km) if float(km).is_integer() else round(km, 1)


def update_calendar(doc, rides):
    """Write the rides (dicts from journal.read_rides) into the Calendrier
    sheet of doc. Returns (number of days, number of week cells) written.
    """
    table = _table(doc, SHEET)
    legend = read_legend(doc, table)
    styles = _auto_styles(doc)
    by_day = defaultdict(list)
    for ride in rides:
        by_day[ride["date"]].append(ride)
    rows = _rows(table)
    days_written = weeks_written = 0
    for first, header, col in list(_months(rows)):
        days_in_month = calendar.monthrange(first.year, first.month)[1]
        days = [first.replace(day=d) for d in range(1, days_in_month + 1)]
        for day in days:
            if day not in by_day:
                continue
            row = _day_row(rows, header, col, day)
            day_rides = by_day[day]
            km_cell = _cell_at(row, col + KM_OFFSET)
            _set_value(km_cell, _km_value(sum(r["km"] for r in day_rides)))
            colors = ride_colors(max(day_rides, key=lambda r: r["km"]), legend)
            base = km_cell.getAttrNS(TABLENS, "style-name")
            if colors and base:
                km_cell.setAttrNS(
                    TABLENS,
                    "style-name",
                    _colored_style(doc, styles, base, colors),
                )
            days_written += 1
        for day in days:
            row = _day_row(rows, header, col, day)
            time_cell = _cell_at(row, col + TIME_OFFSET)
            if time_cell.qname[1] != "table-cell":
                continue  # covered by the merged cell of a previous day
            span = _repeat(time_cell, "number-rows-spanned")
            covered = [d for d in days if 0 <= (d - day).days < span]
            week_rides = [r for d in covered for r in by_day.get(d, [])]
            if week_rides:
                total = sum((r["temps"] for r in week_rides), timedelta(0))
                _set_value(time_cell, total)
                weeks_written += 1
    _drop_cached_results(
        table,
        keep=lambda cell, col: "SUM" not in cell.getAttrNS(TABLENS, "formula"),
    )
    return days_written, weeks_written
