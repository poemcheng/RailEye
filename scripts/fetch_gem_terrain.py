#!/usr/bin/env python3
"""Extract native 81 x 81 GEM-15 DTM cells at RailEye's published regional anchors.

Usage: /usr/bin/python3 scripts/fetch_gem_terrain.py --output data/terrain
Dependencies: GDAL Python bindings with /vsicurl/, numpy, pyproj.
"""
import argparse
import json
import math
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np
from osgeo import gdal
from pyproj import Transformer

CATALOG = 'https://storage.googleapis.com/climate-and-sustainability/gem-15/stac/gem-15'
SOURCE = 'https://developers.google.com/earth-engine/datasets/catalog/projects_climate-and-sustainability_assets_gem-15_v1'
LICENSE = 'https://creativecommons.org/licenses/by/4.0/'
CELL = 15
SIZE = 81
EPSG = 32651
TO_UTM = Transformer.from_crs(4326, EPSG, always_xy=True)
TO_LONLAT = Transformer.from_crs(EPSG, 4326, always_xy=True)
gdal.UseExceptions()
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
gdal.SetConfigOption('CPL_VSIL_CURL_ALLOWED_EXTENSIONS', '.tif')
gdal.SetConfigOption('GDAL_HTTP_TIMEOUT', '60')
gdal.SetConfigOption('GDAL_HTTP_MAX_RETRY', '3')


def signed(index):
    return f'p{index}' if index >= 0 else f'm{-index}'


@lru_cache()
def open_item(west, south):
    group = f'{signed(south // 10 * 10)}_{signed(west // 10 * 10)}'
    tile = f'w{west}s{south}'  # Taiwan is in the NE hemisphere.
    url = f'{CATALOG}/{group}/{tile}/{tile}.json'
    try:
        with urlopen(url, timeout=60) as response:
            stac = json.load(response)
    except HTTPError as ex:
        if ex.code == 404:
            return None
        raise
    asset = stac['assets']['dtm']
    assert stac['bbox'] == [west, south, west + 1, south + 1]
    assert asset['proj:epsg'] == EPSG and asset['proj:transform'][0] == CELL
    ds = gdal.Open('/vsicurl/' + asset['href'])
    assert ds.GetSpatialRef().GetAuthorityCode(None) == str(EPSG)
    x, dx, rx, y, ry, dy = ds.GetGeoTransform()
    assert (dx, rx, ry, dy) == (CELL, 0., 0., -CELL)
    assert x % CELL == y % CELL == 0
    return url, asset, ds


def extract(region):
    lat, lon = region['lat'], region['lon']
    x, y = TO_UTM.transform(lon, lat)
    west = (math.floor(x / CELL) - SIZE // 2) * CELL
    north = (math.floor(y / CELL) + SIZE // 2 + 1) * CELL
    xs = west + (np.arange(SIZE) + 0.5) * CELL
    ys = north - (np.arange(SIZE) + 0.5) * CELL
    pixel_lon, pixel_lat = TO_LONLAT.transform(*np.meshgrid(xs, ys))
    # The polygonal footprint of each 1-degree STAC item defines ownership.
    # Padding in the underlying UTM bounding rectangle must not cross the seam.
    lon_bin, lat_bin = np.floor(pixel_lon).astype(int), np.floor(pixel_lat).astype(int)
    buckets = sorted(set(zip(lon_bin.ravel().tolist(), lat_bin.ravel().tolist())))
    values = np.full((SIZE, SIZE), np.nan, dtype=np.float32)
    assets = []
    for tile_west, tile_south in buckets:
        item = open_item(tile_west, tile_south)
        if item is None:
            continue
        url, asset, ds = item
        x_origin, _, _, y_origin, _, _ = ds.GetGeoTransform()
        xoff, yoff = int((west - x_origin) / CELL), int((y_origin - north) / CELL)
        # Tile rectangles need not span all cells of the surrounding requested window.
        left, top = max(0, -xoff), max(0, -yoff)
        right, bottom = min(SIZE, ds.RasterXSize - xoff), min(SIZE, ds.RasterYSize - yoff)
        if right <= left or bottom <= top:
            continue
        data = ds.GetRasterBand(1).ReadAsArray(xoff + left, yoff + top, right - left, bottom - top)
        mask = (lon_bin[top:bottom, left:right] == tile_west) & (lat_bin[top:bottom, left:right] == tile_south)
        values[top:bottom, left:right][mask] = data[mask]
        assets.append({'stac': url, 'cog': asset['href'], 'productCreated': asset['created']})

    valid = np.isfinite(values)
    center = SIZE // 2
    center_lon = float(pixel_lon[center, center])
    center_lat = float(pixel_lat[center, center])
    center_offset = math.hypot(xs[center] - x, ys[center] - y)
    payload = {
        'id': region['id'] + '-gem15', 'name': region['name'], 'region': region['id'],
        'source': 'Google GEM-15 v1 DTM', 'sourceUrl': SOURCE, 'sourceAssets': assets,
        'edition': 'GEM-15 v1；光學衛星影像取得至 2024 年',
        'license': 'CC BY 4.0', 'licenseUrl': LICENSE, 'attribution': 'This dataset is produced by Google',
        'crs': 'EPSG:32651', 'verticalDatum': 'EGM96（EPSG:5773）',
        'locationStatus': region['location_status'],
        'requestedAnchor': {'lat': lat, 'lon': lon},
        'center': {'lat': center_lat, 'lon': center_lon},
        'centerOffsetM': round(center_offset, 3),
        'status': 'available' if valid.any() else 'unavailable',
        'validCells': int(valid.sum()),
        'coverage': float(valid.mean()),
        'minElevationM': float(values[valid].min()) if valid.any() else None,
        'maxElevationM': float(values[valid].max()) if valid.any() else None,
        'cols': SIZE, 'rows': SIZE, 'cellSize': CELL, 'x0': float(xs[0]), 'y0': float(ys[0]),
        'values': [float(v) if np.isfinite(v) else None for v in values.ravel()],
    }
    return payload


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--regions-script', type=Path, default=Path(__file__).with_name('collect_live.py'))
    args = p.parse_args()
    # Read only the literal public region list; avoid importing collector jobs.
    import ast
    tree = ast.parse(args.regions_script.read_text(encoding='utf-8'))
    regions = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'REGIONS' for t in n.targets))
    args.output.mkdir(parents=True, exist_ok=True)
    for region in regions:
        result = extract(region)
        dst = args.output / (result['id'] + '.json')
        tmp = dst.with_suffix('.tmp')
        tmp.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n',
                       encoding='utf-8')
        tmp.replace(dst)
        print(f"{dst.name}: {result['validCells']}/{SIZE ** 2}, {result['minElevationM']}–{result['maxElevationM']} m",
              flush=True)


if __name__ == '__main__':
    main()
