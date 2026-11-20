# RailEye v0.6 — Terrain Profiles, Drainage and Environmental Monitoring

Traditional-Chinese railway slope decision-support research workspace.
Live site: https://poemcheng.github.io/RailEye/#live

## 地形剖面與坡面排水

開啟 [地形分析](https://poemcheng.github.io/RailEye/#terrain)。在四個區域參考圖幅內繪製多點剖面、讀取高程和縱坡、匯出 CSV，或追蹤 D8 最陡下降流線。點選「同區地形剖面」可從環境或土壤頁直接進入對應區域。也可匯入以公尺為單位的 Arc/Info ASCII Grid。

- Google GEM-15 採 81 × 81 個原生 15 m 格點、EPSG:32651、EGM96。四個圖幅以既有區域參考點為中心，北迴全幅缺值。來源與限制見 [Google 資料說明](https://developers.google.com/earth-engine/datasets/catalog/projects_climate-and-sustainability_assets_gem-15_v1)。This dataset is produced by Google. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- 本土地形採內政部既有 20 m DTM 經 OsmHackTW 轉製的圖磚，取樣為 61 × 61 個 40 m 格點、EPSG:3826。垂直基準待查，單點測製日期未明。ESA WorldCover 2021 遮罩排除永久水體與近水緩衝，來源不明零值一律保留缺值。[地政司資料](https://data.gov.tw/dataset/35430) · [OsmHackTW 轉製版](https://github.com/OsmHackTW/terrain-rgb/tree/eb3ecc4bddb2e28d1f4554ce5c62ef8f112c1bb6) · [ESA 授權與署名](https://esa-worldcover.org/en/data-access)
- 分析操作參考 [CutSheetRX](https://senterfarms.com/programs/csrx/)。RailEye 依原始高程計算，流向遇窪地、平坦面、缺值及邊界停止。貢獻面積為圖幅內有效格點累積面積。各圖幅是靜態區域範例，精密排水設施、流量與崩塌判定需要額外的現地資料。兩來源的圖幅範圍與垂直基準不同。
- 可重現擷取程序在 `scripts/fetch_gem_terrain.py`、`scripts/build_moi_terrain.py`。隨網格提供中央參考點、投影、網格間距、授權與原始資產位置。詳細驗收採 `node tests/terrain-core.cjs` 與 `python scripts/check_terrain_release.py --site _site`。

兩來源對位後，可用配對數為宜蘭 906、內灣 924、南迴 913、北迴 0。網頁顯示同域地勢相關及去除中位數後的高程差異。執行 `python scripts/compare_terrain.py --check` 可重算並查核。

## Environment view
- Open-Meteo current **model estimates**, past modeled rainfall and next 72h weather forecasts.
- WRA public river-level readings with actual station times, raw quality flags and geographical proximity only.
- Official ARDSWC debris-flow/large-landslide alert records, scoped by county.
- NASA ASF Sentinel-1 IW SLC catalog: acquisition time, orbit and optional SAR browse, **not InSAR displacement**.
- NASA POWER long-term monthly climate background with source period and units.
- Optional CWA rain gauge adapter enabled by Actions Secret `CWA_API_KEY`; do not put keys in public JavaScript.

Four regional reference centers are used, not approved railway asset locations. Missing or stale data is never interpreted as safe. No validated slope failure probability, no automatic A–D change, and no train/DWS/TSR controls.

## Refresh
The GitHub Pages workflow collects public data every 30 minutes (UTC minutes 17 and 47), on pushes and manual dispatch. Browser refresh is every 5 minutes while visible; weather, water and alerts attempt direct fetch and otherwise use the clearly timestamped deployment snapshot. Scheduling/provider latency is best effort, not guaranteed safety telemetry. Consult `data/live/health.json` for actual provider status.

## Prior v0.3 features preserved
A–D classification, activity grade separation, interactive basemaps/offline fallback, synthetic observation analysis, local CSV import and collaborative-review demonstration remain available. Official aggregates are the October 20, 2026 TRA briefing snapshot (A0/B3/C1356/D3650; total5009), not current inventory. Synthetic analysis requires explicit selection and is not used to replace unavailable live feeds.

## Run and validate
```
python -m pip install pyproj==3.7.2
node tests/smoke.cjs
node tests/live-core.cjs
python -m unittest discover -s tests -p 'test_live*.py' -v
python scripts/collect_live.py
python -m http.server 8000
```
No credentials are needed for the default sources. Network failures are explicit. See [data contract and operational limits](docs/live-data.md).

## Licensing / deployment
Open-Meteo free API is for noncommercial research and has no SLA. Secure appropriate licenses/service agreements for enterprise production. Respect source attribution/terms. Public repository contains no restricted TRA row-level data or credentials. Official slope/track geometry, engineer Gold Labels, true InSAR and independent prediction validation are still needed for asset-specific research.
