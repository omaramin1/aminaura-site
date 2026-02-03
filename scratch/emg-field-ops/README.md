# EMG Field Operations - Market Map Generator

This directory contains tools for generating verification maps that overlay Opportunity Zones and HUD Qualified Census Tracts on utility service territories.

## Quick Start

```bash
cd scratch/emg-field-ops
python3 filter_zones_dominion.py
```

## Required Data Files

Before running the script, you need to obtain the following GeoJSON files:

### 1. Utility Service Territory
**File:** `dominion_service_area.geojson`

**Sources:**
- Dominion Energy GIS Portal
- [HIFLD Open Data](https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-retail-service-territories) - Electric Retail Service Territories

### 2. Opportunity Zones
**File:** `virginia_opportunity_zones_vedp.geojson`

**Sources:**
- [Virginia Economic Development Partnership (VEDP)](https://www.vedp.org/opportunityzones)
- [CDFI Fund Opportunity Zone Resources](https://www.cdfifund.gov/opportunity-zones)
- [Policy Map](https://www.policymap.com/)

### 3. HUD Qualified Census Tracts (QCT)
**File:** `virginia_qct_2025.geojson`

**Sources:**
- [HUD User QCT Data](https://www.huduser.gov/portal/datasets/qct.html)
- Download the shapefile and convert to GeoJSON using QGIS or ogr2ogr

### 4. Extracted Streets (Optional)
**File:** `batch_extracted_streets.geojson`

**Source:**
- Generated from VIPR (Virginia Information Portal for Renewable Energy) data extraction
- This file is created by the street extraction batch runner

## Output

The script generates: `verify_official_zones_dominion.html`

**Map Layers:**
- Grey: Utility Service Territory (base boundary)
- Blue (#2563eb): Opportunity Zones (clipped to territory)
- Orange (#ff7800): HUD Qualified Census Tracts (clipped to territory)
- Green (#22c55e): Extracted Streets from VIPR

## Adapting for a New Market

1. Obtain GeoJSON files for the new utility territory and state
2. Update the file paths in `filter_zones_dominion.py` (lines 17-20)
3. Update the `OUTPUT_FILE` name (line 23)
4. Run the script

## Dependencies

```bash
pip install geopandas folium
```

## Verification Checklist

After generating the map:

- [ ] Open HTML file in browser
- [ ] Verify blue/orange zones stop exactly at grey utility boundary
- [ ] Check green street polygons appear in expected locations
- [ ] Cross-reference with VIPR portal for accuracy
