#!/usr/bin/env python3
"""
Télécharge les traces GPX des parcours OpenRunner listés dans openrunner_routes.json.

Utilisation :
    python3 -m pip install requests
    python3 download_openrunner.py

Les fichiers sont enregistrés dans ./data/openrunner/<id>.gpx.
Un manifeste CSV est créé/mis à jour dans ./data/openrunner/routes.csv.
Les GPX déjà présents et valides sont conservés, sauf avec --force.
"""

import argparse
import csv
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

API_URL = "https://api.openrunner.com/api/v2/routes/{route_id}/export/gpx-track"
BASE_DIR = Path("data/openrunner")
SCRIPT_DIR = Path(__file__).resolve().parent
ROUTES_FILE = SCRIPT_DIR / "openrunner_routes.json"
ROUTES_CSV = SCRIPT_DIR / "openrunner_routes.csv"
MANIFEST = BASE_DIR / "routes.csv"
USER_AGENT = "OpenRunnerGPXBackup/1.0"
INFO_URL = "https://api.openrunner.com/api/v2/routes/{route_id}"


def is_valid_gpx(path: Path) -> bool:
    try:
        root = ET.parse(path).getroot()
        return root.tag.endswith("gpx")
    except (ET.ParseError, OSError):
        return False


def read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f) if row.get("id")}


def write_manifest(routes: list, results: dict) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "name", "id", "distance_km", "dplus_m", "start", "finish",
        "date", "activity", "gpx_path", "status", "http_status", "message"
    ]
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for route in routes:
            rid = str(route["id"])
            result = results.get(rid, {})
            writer.writerow({
                **route,
                "gpx_path": str((BASE_DIR / f"{rid}.gpx").as_posix()),
                "status": result.get("status", "not_attempted"),
                "http_status": result.get("http_status", ""),
                "message": result.get("message", ""),
            })


def fetch_route_info(session: requests.Session, route_id: str, force: bool = False) -> dict:
    """Download the route description JSON next to its GPX and return it.

    The cached file is reused unless force is True.
    """
    target = BASE_DIR / f"{route_id}.json"
    if target.exists() and not force:
        return json.loads(target.read_text(encoding="utf-8"))
    response = session.get(INFO_URL.format(route_id=route_id),
                           headers={"Accept": "application/json"}, timeout=30)
    response.raise_for_status()
    info = response.json()
    target.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def format_date(date: str) -> str:
    """Convert OpenRunner 'dd.mm yyyy' dates to 'dd/mm/yyyy' (idempotent)."""
    return date.replace(".", "/").replace(" ", "/")


def write_routes(routes: list) -> None:
    """Rewrite the input routes JSON and CSV files, including the activity column."""
    for route in routes:
        route["date"] = format_date(route["date"])
    ROUTES_FILE.write_text(json.dumps(routes, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    fields = [
        "name", "id", "distance_km", "dplus_m", "start", "finish",
        "date", "activity", "gpx_path"
    ]
    with ROUTES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for route in routes:
            writer.writerow({
                **route,
                "distance_km": str(route["distance_km"]).replace(".", ","),
                "gpx_path": f"./data/openrunner/{route['id']}.gpx",
            })


def add_activities(routes: list, force: bool, delay: float) -> None:
    """Fetch each route's activity type and write it to the input files."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    total = len(routes)
    for index, route in enumerate(routes, start=1):
        rid = str(route["id"])
        cached = (BASE_DIR / f"{rid}.json").exists() and not force
        try:
            info = fetch_route_info(session, rid, force)
            route["activity"] = info["data"]["activity"]["name"]
            print(f"[{index:3}/{total}] {rid} — {route['activity']}")
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            route["activity"] = ""
            print(f"[{index:3}/{total}] {rid} — ERROR: {exc}")
        if not cached:
            time.sleep(max(0, delay))
    write_routes(routes)
    print(f"\nUpdated: {ROUTES_FILE}\nUpdated: {ROUTES_CSV}")


def main():
    parser = argparse.ArgumentParser(description="Télécharger les parcours OpenRunner en GPX")
    parser.add_argument("--force", action="store_true",
                        help="retélécharger même si un GPX valide existe déjà")
    parser.add_argument("--delay", type=float, default=0.4,
                        help="pause entre requêtes en secondes (défaut : 0.4)")
    parser.add_argument("--activity", action="store_true",
                        help="fetch route JSON and add the activity column to the input files")
    args = parser.parse_args()

    if not ROUTES_FILE.exists():
        raise SystemExit(f"Fichier introuvable : {ROUTES_FILE}")

    routes = json.loads(ROUTES_FILE.read_text(encoding="utf-8"))
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    if args.activity:
        add_activities(routes, args.force, args.delay)
        return

    old = read_manifest(MANIFEST)
    results = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/gpx+xml, application/xml, text/xml, */*"})

    total = len(routes)
    for index, route in enumerate(routes, start=1):
        rid = str(route["id"])
        target = BASE_DIR / f"{rid}.gpx"

        if target.exists() and is_valid_gpx(target) and not args.force:
            results[rid] = {"status": "already_present", "message": "GPX valide déjà présent"}
            print(f"[{index:3}/{total}] {rid} — déjà présent")
            continue

        url = API_URL.format(route_id=rid)
        try:
            response = session.get(url, timeout=30)
            http_status = response.status_code

            if response.ok:
                # Vérifie le contenu avant d'écrire le fichier final.
                try:
                    root = ET.fromstring(response.content)
                    if not root.tag.endswith("gpx"):
                        raise ValueError("La réponse HTTP ne contient pas un document GPX")
                except (ET.ParseError, ValueError) as exc:
                    message = f"Réponse non GPX : {exc}; extrait={response.text[:120]!r}"
                    results[rid] = {"status": "error", "http_status": http_status, "message": message}
                    print(f"[{index:3}/{total}] {rid} — ERREUR : {message}")
                    continue

                tmp = target.with_suffix(".gpx.tmp")
                tmp.write_bytes(response.content)
                tmp.replace(target)
                results[rid] = {"status": "downloaded", "http_status": http_status, "message": ""}
                print(f"[{index:3}/{total}] {rid} — téléchargé ({len(response.content)} octets)")
            else:
                try:
                    detail = response.text[:200].replace("\n", " ")
                except Exception:
                    detail = "réponse illisible"
                results[rid] = {
                    "status": "error",
                    "http_status": http_status,
                    "message": detail,
                }
                print(f"[{index:3}/{total}] {rid} — HTTP {http_status}: {detail}")

        except requests.RequestException as exc:
            results[rid] = {"status": "error", "message": str(exc)}
            print(f"[{index:3}/{total}] {rid} — ERREUR réseau : {exc}")

        write_manifest(routes, {**old, **results})
        time.sleep(max(0, args.delay))

    write_manifest(routes, {**old, **results})
    downloaded = sum(1 for x in results.values() if x["status"] == "downloaded")
    present = sum(1 for x in results.values() if x["status"] == "already_present")
    errors = sum(1 for x in results.values() if x["status"] == "error")
    print(f"\nTerminé : {downloaded} téléchargé(s), {present} déjà présent(s), {errors} erreur(s).")
    print(f"GPX : {BASE_DIR.resolve()}")
    print(f"Manifeste : {MANIFEST.resolve()}")


if __name__ == "__main__":
    main()
