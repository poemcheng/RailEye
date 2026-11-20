#!/usr/bin/env python3
"""Reproduce regional terrain agreement from released grids (Python 3.10+, pyproj).

Usage: python3 scripts/compare_terrain.py [--directory data/terrain] [--check]
Use --check to verify that the published summary matches the current grids.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import correlation, median

from pyproj import Transformer


def read_grid(directory, entry):
    content = (directory / entry["file"]).read_bytes()
    return json.loads(content), hashlib.sha256(content).hexdigest()


def compare(moi, gem):
    """Pair a land-validated MOI grid center with its nearest native GEM grid cell."""
    project = Transformer.from_crs(moi["crs"], gem["crs"], always_xy=True)
    moi_heights = []
    gem_heights = []
    for index, h_moi in enumerate(moi["values"]):
        if h_moi is None:
            continue
        row, col = divmod(index, moi["cols"])
        easting = moi["x0"] + col * moi["cellSize"]
        northing = moi["y0"] - row * moi["cellSize"]
        x_gem, y_gem = project.transform(easting, northing, errcheck=True)
        # Cell extents are half-open, including their north and west borders.
        gcol = math.floor((x_gem - gem["x0"]) / gem["cellSize"] + 0.5)
        grow = math.floor((gem["y0"] - y_gem) / gem["cellSize"] + 0.5)
        if not (0 <= grow < gem["rows"] and 0 <= gcol < gem["cols"]):
            continue
        h_gem = gem["values"][grow * gem["cols"] + gcol]
        if h_gem is not None:
            moi_heights.append(h_moi)
            gem_heights.append(h_gem)

    result = {"pairedCells": len(moi_heights), "pearsonR": None, "centeredMadM": None}
    if len(moi_heights) < 2 or min(moi_heights) == max(moi_heights) or min(gem_heights) == max(gem_heights):
        return result
    residuals = [m - g for m, g in zip(moi_heights, gem_heights)]
    center = median(residuals)
    result["pearsonR"] = round(correlation(moi_heights, gem_heights), 6)
    result["centeredMadM"] = round(median(abs(d - center) for d in residuals), 3)
    return result


def summarize(directory):
    catalog = json.loads((directory / "catalog.json").read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in catalog}
    regions = {}
    for region in dict.fromkeys(e["region"] for e in catalog):
        moi_id, gem_id = region + "-moitw", region + "-gem15"
        if moi_id not in by_id or gem_id not in by_id:
            continue
        moi, moi_hash = read_grid(directory, by_id[moi_id])
        gem, gem_hash = read_grid(directory, by_id[gem_id])
        regions[region] = {"moiGrid": moi_id, "gemGrid": gem_id, "moiSha256": moi_hash,
                           "gemSha256": gem_hash, **compare(moi, gem)}
    return {
        "schemaVersion": 1,
        "method": {
            "pairing": "MOI 40 m 格心投影至 GEM-15 原生平面座標，配對涵蓋該點的最近格心。限兩來源皆有值；不跨缺值格搜尋。",
            "pearsonR": "共同有效點的兩來源高程 Pearson 相關係數。",
            "centeredMadM": "每對差值 d = MOI − GEM。以公尺計算 median(|d − median(d)|)，未作常態尺度換算。",
            "eligibility": "配對少於兩格，或任一來源的配對高程全部相同時，兩個地勢比較統計量均留空。",
            "scope": "用於比較共同覆蓋區域的相對地勢；空間相鄰格有自相關，兩來源時期、解析度、垂直基準不同。"
        },
        "regions": regions
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "terrain")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = summarize(args.directory)
    output = args.directory / "comparison.json"
    if args.check:
        if not output.exists() or json.loads(output.read_text(encoding="utf-8")) != summary:
            raise SystemExit("Terrain comparison requires regeneration")
    else:
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
    for region, row in summary["regions"].items():
        print(region, row["pairedCells"], row["pearsonR"], row["centeredMadM"])


if __name__ == "__main__":
    main()
