# RailEye v0.4 — Environmental Monitoring and Geotechnical Evidence

Traditional-Chinese railway slope decision-support research workspace.
Live site: https://poemcheng.github.io/RailEye/#live

## New environment view
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
