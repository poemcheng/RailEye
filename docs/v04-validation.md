# RailEye v0.4 validation record

Code: existing v0.3 checks 28/28; new temporal/forecast core 30/30; source collector and ASF/climatology regression checks 26/26 on GitHub Actions.

Local browser acceptance: 22/22 checks with explicit synthetic test fixtures; separate nine checks rendered the deployed artifact and real public snapshot captured 2026-11-16T16:56:51Z. All four region outputs rendered, original grading view preserved, 1540/1024/390px overflow checks passed, no page JavaScript errors. Local outbound transport was disabled. These are not claims of interactive public-site browser verification.

Actual provider calls on the GitHub runner succeeded for weather/climate/ASF in all four regions, WRA gauges and metadata, and ARDSWC official alerts. Optional CWA remained requires_configuration. Near-45-day SLC catalog results: northlink9/yilan9/southlink10/neiwan9; shared acquisitions overlap across regions and must not be counted as independent scenes. No SLC binary downloads or InSAR displacement products were generated.

Public HTTPS acceptance is checked after each deployment by scripts/check_live_release.py: index, exact commit build-info and schema-valid published data. Source statuses and original timestamps remain visible. Successful HTTP delivery does not validate geotechnical predictions.

No synthetic weather/hydrology fallback, no slope-failure probabilities, no train-control integration. Forecast probabilities refer only to hourly precipitation; no-response/no-alert/low-rainfall must never be interpreted as proof of slope safety.
