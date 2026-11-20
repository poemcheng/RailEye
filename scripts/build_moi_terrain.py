"""Extract regional reference grids from pinned MOI-derived DEM tiles.

Requires GDAL's Python bindings, Pillow and NumPy. Example from the repo root:
python3 scripts/build_moi_terrain.py --output data/terrain --cache /tmp/rail-dem
The source data, projection and coastline mask are documented in every JSON.
"""
import argparse
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from osgeo import gdal, osr
from PIL import Image

REVISION = "eb3ecc4bddb2e28d1f4554ce5c62ef8f112c1bb6"
TILES = f"https://raw.githubusercontent.com/OsmHackTW/terrain-rgb/{REVISION}/tiles/12"
SOURCE = "https://data.gov.tw/dataset/35430"
DERIVATIVE = f"https://github.com/OsmHackTW/terrain-rgb/tree/{REVISION}"
MASK_ROOT = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
MASK_DIGESTS = {
    21: "b23a186262569b69c05b7638e6fa0645a7376ebbb2644a8eac8c58fa8a767bd2",
    24: "730c11c72158595d6fcc9b0fe4a61ff2fb786e17f08a3412542ce7e4de17a3c9"
}
SIDE, STEP = 61, 40
GLOBE = 4096 * 256


def read_file(url, dest, expected=None):
    if not dest.exists():
        with urlopen(url, timeout=60) as response:
            data = response.read()
        if expected and sha256(data).hexdigest() != expected:
            raise ValueError(f"Unexpected source hash for {dest.name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        temporary = dest.with_suffix(dest.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(dest)
    data = dest.read_bytes()
    if expected and sha256(data).hexdigest() != expected:
        raise ValueError(f"Unexpected cached source hash for {dest.name}")
    return data


def reference(epsg):
    result = osr.SpatialReference()
    result.ImportFromEPSG(epsg)
    result.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return result


def land_mask(cache, lat, x0, y0):
    # At a 40 m target grid, sample its footprint and a 20 m guard band against
    # fixed 2021 water/unknown classes; conservation here matters more than area.
    south = int(lat // 3) * 3
    filename = f"ESA_WorldCover_10m_2021_v200_N{south}E120_Map.tif"
    url = f"{MASK_ROOT}/{filename}"
    path = cache / filename
    read_file(url, path, MASK_DIGESTS[south])
    src = gdal.Open(str(path))
    if src is None:
        raise ValueError(f"Unreadable land mask {filename}")
    west, north = x0 - STEP, y0 + STEP
    east, bottom = x0 + SIDE * STEP, y0 - SIDE * STEP
    # 10 m point samples cover the footprint plus a peripheral 20 m guard.
    fine = gdal.Warp("", src, format="MEM", dstSRS="EPSG:3826",
                     outputBounds=(west, bottom, east, north), xRes=10, yRes=10,
                     resampleAlg="near", overviewLevel="NONE", dstNodata=0)
    fine_values = fine.ReadAsArray()
    # Code 0 is missing coverage; 80 is permanent water. Reject unknown codes.
    valid = np.isin(fine_values, [10, 20, 30, 40, 50, 60, 70, 90, 95, 100])
    mask = np.empty((SIDE, SIDE), dtype=bool)
    for row in range(SIDE):
        for col in range(SIDE):
            mask[row, col] = valid[4*row:4*row+8, 4*col:4*col+8].all()
    return mask, {"dataset": "ESA WorldCover 2021 v200", "url": url,
                  "sha256": MASK_DIGESTS[south], "license": "CC BY 4.0",
                  "credit": "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium"}


def build(region, cache):
    id_, lat, lon = region["id"], region["lat"], region["lon"]
    forward = osr.CoordinateTransformation(reference(4326), reference(3826))
    inverse = osr.CoordinateTransformation(reference(3826), reference(4326))
    cx, cy, _ = forward.TransformPoint(lon, lat)
    x0 = round(cx / STEP) * STEP - SIDE // 2 * STEP
    y0 = round(cy / STEP) * STEP + SIDE // 2 * STEP
    land, mask_info = land_mask(cache, lat, x0, y0)
    assets = {}

    @lru_cache(None)
    def image(x, y):
        url = f"{TILES}/{x}/{y}.png"
        data = read_file(url, cache / f"z12_{x}_{y}.png")
        assets[url] = sha256(data).hexdigest()
        return Image.open(BytesIO(data)).convert("RGBA")

    values = []
    for r in range(SIDE):
        for c in range(SIDE):
            if not land[r,c]:
                values.append(None)
                continue
            lng, latitude, _ = inverse.TransformPoint(x0 + c*STEP, y0 - r*STEP)
            px = math.floor((lng + 180) / 360 * GLOBE)
            py = math.floor((1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2 * GLOBE)
            red, green, blue, alpha = image(px // 256, py // 256).getpixel((px % 256, py % 256))
            decimetres = (red << 16) + (green << 8) + blue - 100000
            # Original conversion removes NoData metadata. A true zero cannot
            # be distinguished from a padded zero; exclude both conservatively.
            known = alpha == 255 and -1000 < decimetres <= 40000 and decimetres != 0
            values.append(decimetres / 10 if known else None)
    center_e = x0 + SIDE // 2 * STEP
    center_n = y0 - SIDE // 2 * STEP
    center_lon, center_lat, _ = inverse.TransformPoint(center_e, center_n)
    return {
        "id": id_ + "-moitw", "region": id_, "name": region["name"],
        "crs": "EPSG:3826", "verticalDatum": "轉製圖磚未標示可核驗的垂直基準",
        "source": "內政部地政司 DTM／OsmHackTW 圖磚", "sourceUrl": SOURCE,
        "derivedFrom": DERIVATIVE,
        "license": "原始高程：政府資料開放授權條款第1版；OsmHackTW 圖磚儲存庫：GPL-3.0；水域遮罩：CC BY 4.0",
        "licenseUrls": ["https://data.gov.tw/license", "https://github.com/OsmHackTW/terrain-rgb/blob/main/LICENSE",
                        "https://creativecommons.org/licenses/by/4.0/"],
        "edition": "地政司 2016 年上架資料集 35430；各點測製日期未標示",
        "cols": SIDE, "rows": SIDE, "cellSize": STEP, "x0": x0, "y0": y0, "values": values,
        "requestedAnchor": {"lat": lat, "lon": lon},
        "center": {"lat": center_lat, "lon": center_lon},
        "locationStatus": region["location_status"],
        "centerOffsetM": round(math.hypot(center_e-cx, center_n-cy), 1),
        "processing": "20 m 原始 DTM 經 OsmHackTW 最近鄰轉製為 z12 圖磚（此緯度約 35 m），再以最近鄰擷取 40 m 等距格。40 m 格內或周圍 20 m 經 ESA 2021 判為永久水域或無覆蓋，以及來源不明零值，均以缺值顯示。",
        "assets": [{"url": url, "sha256": digest} for url,digest in sorted(assets.items())],
        "waterMask": mask_info, "maskedCells": int((~land).sum()),
        "validCells": sum(v is not None for v in values),
        "credits": "原始地形由內政部地政司提供，OsmHackTW 轉製地形圖磚；水域遮罩由 RailEye 依 ESA WorldCover 2021 製作。"
    }


def main():
    from collect_live import REGIONS
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    for region in REGIONS:
        grid = build(region, args.cache)
        out = args.output / (grid["id"] + ".json")
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(grid, ensure_ascii=False, separators=(",",":"), allow_nan=False) + "\n", encoding="utf-8")
        tmp.replace(out)
        print(out.name, grid["validCells"], "/", SIDE**2, "center",grid["values"][SIDE**2//2])


if __name__ == "__main__":
    gdal.UseExceptions()
    main()
