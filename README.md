# RailEye v0.3｜鐵路邊坡地工分析工作站

Website: https://poemcheng.github.io/RailEye/

A Traditional Chinese, source-backed public geotechnical UI. This release replaces the v0.2 schematic-only screen with an interactive map, TRA classification views, observation analytics and local collaboration examples.

## Five views

1. **總覽**: pan/zoom street or topographic basemap, official aggregates, evidence cards and six explicitly synthetic cases.
2. **分級**: separate TRA A–D maintenance classes and technology-survey activity classes; actual historical counts and recommendation matrix.
3. **監測**: LOS time series, coherence filter, observation-day rainfall, availability-time replay and local CSV import. Synthetic data are opt-in; unavailable real observations stay unavailable.
4. **協作**: local demonstration tasks, mandatory handoff reasons and audit entries. Not official dispatch, signatures or safety acknowledgement.
5. **來源**: international design references, provenance, data gates and limitations.

## Verified historical aggregates

Source: user-provided `1151020臺鐵邊坡實務與資料應用說明會2.0 - 鐵客松 - 寄出.pdf`, 2026-10-20 snapshot.

- p.3–4: 5,009 registered slopes: A=0, B=3, C=1,356, D=3,650.
- p.9,12: 1,096 concern areas; 175 medium-high/high activity areas (104+71); 921 medium/low areas.
- p.12: LiDAR 15, corner reflectors 5, GNSS 8, geotechnical instruments 5; other improvement/monitoring/authority coordination 142. These are recommendations, not completed projects.

No raw TRA files, restricted row-level records or approved asset geometries are published. Do not equate a synthetic A-grade case with official counts. Activity class is not interchangeable with A–D or a calibrated hazard probability.

## Data import

UTF-8, unquoted CSV; exact header:

```csv
observed_at,available_at,los_mm,coherence,rain_mm
2026-01-01T00:00:00Z,2026-01-03T00:00:00Z,-1,0.8,5
```

The row above is an example, not a measurement. Blank numeric cells remain null. Timestamps require time zones. Availability cannot precede observation. Coherence must be within 0–1, rainfall nonnegative. Limits: 2 MB / 5,000 rows. Imported observations remain in tab memory only and are labelled unverified. The replay cutoff is based on sorted unique availability timestamps, including delayed publication. LOS sign displayed by this UI is positive towards the satellite, negative away; normalize source units and signs before import. Rainfall is the daily value at each observation date, not accumulated rainfall between satellite visits.

## Local run and tests

Open `index.html` with a modern browser, or serve this directory with a static HTTP server. No build or runtime package installation is required.

```sh
node --check app.js
node tests/smoke.cjs
```

28 numerical/parser tests and 41 Chromium UI checks passed locally. See `docs/validation.md` for what was and was not tested. GitHub Actions reruns JavaScript syntax and the numerical/parser suite before publishing only the public site files.

## Map and privacy

Online maps request only visible tiles from OpenStreetMap or OpenTopoMap and retain visible attribution. Do not prefetch or bulk-download tiles. These providers can observe normal browser requests/IP/referrer; do not use sensitive internal coordinates on public third-party basemaps without authorization. Failure falls back to a low-resolution Natural Earth coastline, not fake terrain. Maps are not approved railway engineering geometry.

Synthetic workflow notes may use localStorage on this browser; no shared backend, authentication, cross-device synchronization or electronic signature is provided. Do not enter sensitive information. Imported CSV observations are not stored in localStorage or sent to a server. No analytics telemetry is included.

## Safety boundary

No actual SLC/InSAR products, live rainfall, validated prediction, official per-slope GIS or railway control connections are included. Quality filtering does not certify measurements. LOS is not vertical settlement. No factor of safety, collapse time or trained risk probability is computed. Existing DWS/TSR/signalling remains completely separate.

## References and release

See `docs/design-sources.md`. Reference platforms inspire interaction patterns; no proprietary interface/code or data are copied. Main-branch changes trigger GitHub Pages after tests. `build-info.json` exposes the deployed version/commit. Code publication is not enterprise acceptance, safety certification or demonstrated human-factor benefit.
