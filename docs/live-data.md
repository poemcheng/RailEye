# RailEye v0.4 — public data contract and operational limits

## Actual sources (no synthetic fallback)

- Weather: https://open-meteo.com/en/docs — current values and past hours are **model estimates**, future hours are weather forecasts. The API does not provide an authoritative run issue time in this response: `model_issue_time=null`. Past 24h is **not** CWA measured rainfall.
- River level: https://data.gov.tw/dataset/25768 and station metadata https://data.gov.tw/dataset/22227 — use the explicit station timestamp, preserve source quality, and never compare elevations between unrelated gauges. Nearness <=60km is merely geographic context, not watershed connectivity.
- Slope/debris alerts: https://data.moa.gov.tw/open_detail.aspx?id=ofvJwoWC5wum — original official alerts, filtered by county. The documented no-alert placeholder is normalized to an empty list. Empty is NOT a statement that slopes are safe. No alerts are suppressed based on assumptions about their duration.
- Satellite: https://docs.asf.alaska.edu/api/keywords/ — most recent catalog entries among up to 60 Sentinel-1 IW SLC results intersecting the regional reference point in the last 45 days; list is capped and disclosed. A browse image is SAR intensity, **not** displacement, coherence or InSAR.
- Climate: https://power.larc.nasa.gov/docs/services/api/temporal/climatology/ — monthly climatology, with period and units as returned by NASA. `PRECTOTCORR` mm/day must not be labelled monthly accumulated mm. This is gridded background, not a slope station observation.
- Optional CWA: O-A0002-001 via secret `CWA_API_KEY`, supplied only to the collector process. No key = explicit configuration gate. Never put the key into JS, URLs in public files, or logs.

## Acquisition and publishing

GitHub Actions runs on main pushes, manual dispatch and cron `17,47 * * * *` (UTC, every half-hour). The collector fetches 4 regional references, independent sources run with a maximum concurrency of 4, HTTPS host allowlist, timeout, bounded response size, retry and per-source error state. Public climatology and WRA station metadata are cached separately (30 days / 1 day); no secrets are cached. All public outputs are staged in `_site/data/live` and deployed, not committed every half-hour.

The frontend reads that snapshot every 5 minutes while visible, and attempts direct CORS-permitted weather, WRA and alert calls. Direct failures keep the *original* snapshot timestamp and are disclosed. Browser timer is paused when hidden. Automatic refresh can be disabled. Satellite/climatology are updated by the workflow, not by submitting processing jobs from the browser.

GitHub schedules are best-effort, may be delayed/dropped and public schedules can be disabled after inactivity. This is not 24/7 safety telemetry. Provider downtime and CORS restrictions remain visible; no fabricated green/normal status is used. Open-Meteo free API is noncommercial, rate limited and has no availability SLA: https://open-meteo.com/en/pricing . Obtain appropriate access/service terms before enterprise/commercial operation.

## Forecast arithmetic

Precipitation values are sums for the preceding hour. At wall time t, past estimates end at floor(t/hour); forecasts start at ceil(t/hour). We deliberately omit the current partially elapsed hour from full-hour accumulations. A 24h sum requires 24 unique, finite, nonnegative hourly observations. Missing/duplicate entries produce null, not zero. The plotted series leaves the partial hour gap. Hourly precipitation probability maximum is explicitly labelled; it is not a 24h cumulative probability or a slope failure probability.

## Location and safety boundary

Four hand-selected regional reference centers (Hualien north, Suao, Taimali, Neiwan) are openly disclosed and **not** asset coordinates. No confidential TRA source rows are uploaded. Official TRA 2026-10-20 aggregate displays remain separate from this environmental view.

No A-D automatic grading, no slope failure probability, no collision countdown, no DWS/TSR writes, no field-entry authorization. Valid slope predictions remain gated on approved asset identity, engineering evidence, event labels and independent calibration.

## Test scope

`node tests/smoke.cjs`: existing 28 checks.
`node tests/live-core.cjs`: 30 temporal/missingness/forecast/gauge checks.
`python -m unittest discover -s tests -p test_live.py -v`: 22 collector tests with mocks.
`python tests/browser_live.py`: local Chromium checks using explicitly synthetic test fixtures; not a provider/network acceptance test. These fixtures are not deployed.

Remote workflow logs and `data/live/health.json` establish which real upstream calls actually succeeded on each run. A passing mock test does not prove external feeds are working.
