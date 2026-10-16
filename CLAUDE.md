# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Generate yearly cycling program graphs (saves PNG files)
python show_graphs.py bike save 2

# Display graph on screen (only first program)
python show_graphs.py bike show 1

# Print raw ODS data
python show_graphs.py print /path/to/program.ods

# Analyze a FIT file
python show_graphs.py fit /path/to/file.fit

# Run web server
gunicorn visu_velo_web:app
```

There are no automated tests.

## Architecture

The pipeline is: ODS/FIT file → `velo_tools/readers.py` → `velo_tools/graphers.py` → PNG or web.

**`velo_tools/readers.py`**
- `ods_to_df(file_path)` — reads the "Journal" sheet (header row 4, date index at column 3) from a cycling program ODS file; reindexes to a full Nov 1 → Oct 31 season date range
- `summarize(my_df)` — adds a `week_sum` column (total km per week, keyed to Mondays)
- `fit_to_df(path)` — reads a CSV-format FIT export (not raw FIT binary); returns a DataFrame indexed by date

**`velo_tools/graphers.py`**
- `show_resume(my_df)` — produces a 3-subplot matplotlib figure (20×8 in): elevation per ride + cumulative D+, daily km by training zone + speed spline, weekly km bars + cumulative distance
- Training zone colors are defined inline in `show_resume`; NaN type defaults to `"inconnu"` (light green)
- French locale is set at call time: `locale.setlocale(locale.LC_TIME, 'fr_FR.utf8')`

**`show_graphs.py`** — CLI entry point; hardcodes ODS file paths to `/home/richard/03COMMON/0000velo/ProgrammeCyclo_*.ods`

**`visu_velo_web.py` / `web/`** — Flask app with three routes: `/` (home), `/matplotlib` (PNG embed), `/velo` (Bokeh interactive chart). Deployed via Heroku (`Procfile`).

**Utility scripts** (standalone, not imported elsewhere):
- `stravagpx2csv.py` — GPX → CSV conversion
- `merge_gpx.py` — merges multiple GPX files
- `reduce_1s_to_1m.py` — downsamples 1-second CSV data to 1-minute averages
- `csv_analysis.py` — heart rate zone analysis from CSV
- `fit_analyse.py` — detects sustained effort periods in FIT data to estimate LTHR

## Key data notes

- ODS files use activity columns: `type, km, temps, elev, zone, moy`
- `fit_to_df` reads a **CSV** (not binary FIT); the raw-to-CSV conversion happens outside this repo
- Season bounds: November 1 of the first data year through October 31 of the next
