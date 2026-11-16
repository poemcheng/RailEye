# v0.3 Validation record

Local checks performed 2026-11-16.

## Executed

- `node --check app.js`: passed.
- `node tests/smoke.cjs`: 28/28 passed. Covers official totals, action-category totals, synthetic identity, missingness, CSV columns/timezone/duplicates/numerical ranges, availability-time exclusion, quality filter and Web Mercator roundtrip.
- Chromium with Playwright, local HTML loaded through `set_content`: 41/41 passed. Covers five views, data-mode isolation, no fabricated official records, six synthetic cases, route/grade filters including empty results, linked detail, map zoom/reset, quality threshold, replay, local import, delayed publication, local workflow, required reasons/audit, reference links and responsive widths 1440/1024/390. No JavaScript errors observed.
- Local desktop screenshots reviewed for overview, grading and analysis; mobile layout inspected.
- index.html, styles.css and app.js Git blob hashes compared with the tested local files before commit.

## Important limits

The test container cannot reach external basemap services or navigate a locally served origin. Local UI tests used inline CSS/JS on a Chromium `set_content` document. These are real rendered code tests, not AI-generated screenshots, but they are NOT a public-site end-to-end test. Real-origin localStorage persistence, remote tile delivery, clipboard downloads and all operating systems/browsers are not fully validated. Unsupported storage is handled with a visible memory-only warning.

No ground truth, real InSAR, coordinates, prediction calibration, user workload improvement or safety performance was validated by these software tests. The uploaded CSV contract is narrow and unquoted; source geodetic references, LOS sign, instruments and provenance must be normalized outside this public demonstration.

## Release gate

GitHub Pages workflow runs syntax and numerical/parser tests, then stages only index.html, styles.css, app.js, .nojekyll and generated build-info.json. Only a successful deployment job establishes a GitHub Pages release; it does not establish field acceptance.
