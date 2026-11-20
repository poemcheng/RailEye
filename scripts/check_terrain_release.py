"""Verify staged terrain assets, grid metadata and the actual GitHub Pages release."""
import argparse
import json
import math
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

VERSION = "0.6.0"
BASE = "https://poemcheng.github.io/RailEye/"
ASSETS = ("terrain-core.js", "terrain-ui.js", "terrain.css")
METADATA = ("id", "region", "name", "crs", "verticalDatum", "source", "sourceUrl", "license", "edition")
SITE = Path(__file__).resolve().parents[1] / "_site"


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def text_fields(obj, fields):
    return isinstance(obj, dict) and all(isinstance(obj.get(k), str) and obj[k].strip() for k in fields)


def check_grid(entry, grid):
    if not text_fields(grid, METADATA) or any(grid[k] != entry[k] for k in ("id", "region")):
        raise ValueError(f"{entry['id']}: invalid metadata or mismatched catalog identity")
    if not grid["sourceUrl"].startswith("https://"):
        raise ValueError(f"{entry['id']}: missing HTTPS source link")
    rows, cols, values = grid.get("rows"), grid.get("cols"), grid.get("values")
    if type(rows) is not int or type(cols) is not int or min(rows, cols) < 1:
        raise ValueError(f"{entry['id']}: invalid grid dimensions")
    if not all(finite(grid.get(k)) for k in ("x0", "y0", "cellSize")) or grid["cellSize"] <= 0:
        raise ValueError(f"{entry['id']}: invalid metric grid geometry")
    if not isinstance(values, list) or len(values) != rows * cols:
        raise ValueError(f"{entry['id']}: unexpected number of heights")
    if any(value is not None and not finite(value) for value in values):
        raise ValueError(f"{entry['id']}: heights must be finite or null")
    valid = sum(value is not None for value in values)
    if "validCells" in grid and (type(grid["validCells"]) is not int or grid["validCells"] != valid):
        raise ValueError(f"{entry['id']}: validCells disagrees with raster")
    unavailable = grid.get("status") == "unavailable"
    if valid == 0 and (not unavailable or grid.get("validCells") != 0):
        raise ValueError(f"{entry['id']}: completely masked crop requires explicit unavailable status and validCells=0")
    if valid and unavailable:
        raise ValueError(f"{entry['id']}: unavailable status disagrees with populated raster")
    return valid


def check_site(read, expected_sha):
    build = json.loads(read("build-info.json"))
    if build.get("version") != VERSION or (expected_sha and build.get("commit") != expected_sha):
        raise ValueError("unexpected build version or commit")
    html = read("index.html").decode("utf-8")
    if 'id="view-terrain"' not in html:
        raise ValueError("missing terrain view")
    for asset in ASSETS:
        if f'{asset}?v={VERSION}' not in html or not read(asset).strip():
            raise ValueError(f"missing terrain asset {asset}")
    catalog = json.loads(read("data/terrain/catalog.json"))
    if not isinstance(catalog, list) or not catalog:
        raise ValueError("empty terrain catalog")
    counts, files = {}, set()
    for entry in catalog:
        if not text_fields(entry, ("id", "region", "label", "file")):
            raise ValueError("invalid terrain catalog entry")
        filename = entry["file"]
        if filename == "catalog.json" or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\.json", filename):
            raise ValueError("grid path must be a JSON basename")
        if entry["id"] in counts or filename in files:
            raise ValueError("duplicate terrain grid in catalog")
        files.add(filename)
        counts[entry["id"]] = check_grid(entry, json.loads(read("data/terrain/" + filename)))
    if not any(counts.values()):
        raise ValueError("no valid elevations in published coverage")
    return {"commit": build.get("commit"), "valid_cells": counts}


def read_public(path):
    request = Request(f"{BASE}{path}?terrain_check={time.time_ns()}",
                      headers={"User-Agent": "RailEye-Terrain/0.6", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", action="store_true", help="check deployed HTTPS assets")
    parser.add_argument("--site", type=Path, default=SITE, help="staged site directory")
    args = parser.parse_args()
    expected = os.environ.get("GITHUB_SHA")
    attempts = 5 if args.public else 1
    for attempt in range(attempts):
        try:
            read = read_public if args.public else lambda path: (args.site / path).read_bytes()
            summary = check_site(read, expected)
            print("TERRAIN_ACCEPTANCE", json.dumps(summary, ensure_ascii=False))
            return
        except (ValueError, OSError) as error:
            if attempt == attempts - 1:
                raise
            print(f"Retrying terrain release check: {error}")
            time.sleep(6)


if __name__ == "__main__":
    main()
