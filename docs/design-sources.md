# Design sources / 2026-11-16

## International primary sources

| Source | Pattern adopted | Boundary |
|---|---|---|
| [Copernicus EGMS](https://land.copernicus.eu/en/products/european-ground-motion-service) | Map-linked LOS displacement time series and measurement quality | European coverage, not a Taiwanese InSAR source |
| [GroundProbe MonitorIQ Next / Orica](https://www.orica.com/en/digital-solutions/geosolutions/groundprobe/monitoriq-next) | Multiple coordinated geotechnical charts and observation context | No product integration, commercial data or collapse prediction copied |
| [Hong Kong CEDD Slope Information System](https://www.cedd.gov.hk/eng/our-major-services/geotechnical/slope-information/index.html) | Asset-centric spatial and maintenance records | Hong Kong records/classes do not substitute for TRA assets/classes |
| [NASA GPM / LHASA viewer](https://pmmpublisher.pps.eosdis.nasa.gov/precip-apps-viewer.html) | Separate rain, hazard/exposure layers and timestamps | No LHASA output is served or treated as a TRA classification |

## TRA source

The user-supplied 2026-10-20 briefing is the numerical authority, not prior generated mockups. Pages 3–4 support A–D definitions and counts; page 9 supports broad-area / hotspot / near-field workflow; page 12 supports 1,096/175/921 and the high/medium-high action table. Pages 10–11 describe existing safety systems that this application does not control.

The interface is a faithful summary, not a replacement for the latest approved maintenance manual. Inspection frequencies are deliberately not hard-coded from a presentation snapshot. No unsupported A–D-by-activity cross-table is generated.

## Basemap and geometry

- [OpenStreetMap attribution](https://www.openstreetmap.org/copyright)
- [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/): visible tiles only, normal HTTP caching, visible attribution and browser referrer.
- [OpenTopoMap](https://opentopomap.org): map data OSM/SRTM, rendering CC-BY-SA attribution shown.
- [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/): public-domain low-resolution geometry.
- Coastline extracted from [Natural Earth 1:110m countries](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson). It is an offline fallback, not terrain, an engineering survey or an official boundary statement.

Regional navigation centers and SIM locations are not railway assets. No route polyline is fabricated as a surveyed railway. All SIM data and analytic sequences are generated for interaction tests and always identified as synthetic.
