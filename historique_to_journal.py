#!/usr/bin/env python3
"""Add a Journal sheet to an old ProgrammeCyclo ODS from its Historique sheet.

Usage:
    python historique_to_journal.py ProgrammeCyclo_22-23.ods [--dry-run]

Only bike rides are copied; type and zone are left empty, RPE, max HR and
max speed go to the comment. A backup <file>.bak is written before saving.
"""

import argparse
import shutil
import sys
from pathlib import Path

from odf.opendocument import load

from velo_tools.journal import add_journal_sheet, read_historique


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ods", type=Path)
    parser.add_argument(
        "--dry-run", action="store_true", help="list rides only"
    )
    args = parser.parse_args()

    doc = load(str(args.ods))
    rides = read_historique(doc)
    for ride in rides:
        print(
            f"{ride['date']:%d/%m/%y}  {ride['destination']:<20}"
            f" {ride['km']:>5} km  {ride['temps']}  {ride['elev']} m+"
            f"  {ride['comment'] or ''}"
        )
    print(f"{len(rides)} rides")
    if args.dry_run:
        return
    try:
        add_journal_sheet(doc, rides)
    except ValueError as error:
        sys.exit(str(error))
    backup = args.ods.with_name(args.ods.name + ".bak")
    shutil.copy2(args.ods, backup)
    doc.save(str(args.ods))
    print(f"Backup in {backup}, Journal added to {args.ods}")


if __name__ == "__main__":
    main()
