# RailEye Live v0.2

Evidence-led railway slope inspection and human–AI decision-support **public demonstrator** (繁體中文).

## Open
- Repository: https://github.com/poemcheng/RailEye
- Intended Pages URL: https://poemcheng.github.io/RailEye/ **(only after GitHub Pages is enabled and deployment succeeds)**
- Local: download the repository and open `index.html` directly. No server, credentials or installation required.

## Features
- Responsive all-Taiwan **schematic** rail map and three selectable synthetic cases.
- Independent A–D maintenance-grade and InSAR activity-grade fields.
- Provenance/quality cards, explicit missingness, no invented risk probabilities.
- Simulated evidence time replay (not historic observations or live satellites).
- Suggested next review action and demo handoff notes saved to the local browser only.
- Filter by route/task, toggle thematic layers, copy synthetic evidence brief.

## Boundaries
All map pins and sampled cases are **synthetic**, not actual slopes or official railway chainage. Counters (5,009 registered slopes; 1,096 broad-area inspection regions; 175 medium-high/high activity regions) are historical aggregates from the Taiwan Railway 2026-10-20 practical briefing, *not current operational data*. No official GIS line geometry, approved asset locations, live InSAR, rainfall telemetry, validated hazard model, real work orders, train positions or railway safety-control connection.

The prototype cannot change railway operating restrictions, signalling, DWS/TSR, or official maintenance grades. Do not publish restricted TRA competition records into this public repository.

## Deploy with GitHub Pages
1. On GitHub, open **Settings → Pages**.
2. Under **Build and deployment**, choose **GitHub Actions** as Source.
3. The included `.github/workflows/pages.yml` will deploy `index.html` from `main`.
4. Check **Actions** for the workflow result; open https://poemcheng.github.io/RailEye/ only after successful deployment.

If GitHub Pages deployment protection or repository policy requires approval, complete the action in GitHub. This README doesn't assert that Pages is already live.

## Future professional edition
Authorized GIS/asset crosswalk → InSAR/observation validity → as-of-time provenance → verified engineer review → spatial/temporal external validation → human-factor trial. Keep approved safety systems autonomous and separate.
