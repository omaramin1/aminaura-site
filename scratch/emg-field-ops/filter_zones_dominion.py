#!/usr/bin/env python3
"""
Market Map Generator for Dominion Energy Territory
Generates an interactive HTML map that overlays:
- Opportunity Zones (blue)
- HUD Qualified Census Tracts (orange)
- Extracted Streets (green)
All clipped to the Utility Service Territory boundary.
"""

import geopandas as gpd
import folium
from folium import GeoJson, LayerControl
import os
import pandas as pd

# =============================================================================
# CONFIGURATION - Update these paths for different markets
# =============================================================================

# Input file paths
UTILITY_BOUNDARY = "dominion_service_area.geojson"
OPPORTUNITY_ZONES = "virginia_opportunity_zones_vedp.geojson"
QCT_ZONES = "virginia_qct_2025.geojson"
STREET_DATA = "batch_extracted_streets.geojson"

# Output file
OUTPUT_FILE = "verify_official_zones_dominion.html"

# Map styling
UTILITY_STYLE = {
    "fillColor": "#808080",
    "color": "#505050",
    "weight": 2,
    "fillOpacity": 0.15,
}

OZ_STYLE = {
    "fillColor": "#2563eb",
    "color": "#1d4ed8",
    "weight": 1,
    "fillOpacity": 0.4,
}

QCT_STYLE = {
    "fillColor": "#ff7800",
    "color": "#cc6000",
    "weight": 1,
    "fillOpacity": 0.4,
}

STREET_STYLE = {
    "fillColor": "#22c55e",
    "color": "#16a34a",
    "weight": 2,
    "fillOpacity": 0.6,
}

# =============================================================================
# MAIN PROCESSING LOGIC
# =============================================================================

def prepare_for_json(gdf):
    """Convert any timestamp/datetime columns to strings for JSON serialization."""
    if gdf is None:
        return None
    gdf = gdf.copy()
    for col in gdf.columns:
        if col == 'geometry':
            continue
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
    return gdf


def load_geojson(filepath, name):
    """Load a GeoJSON file and handle errors gracefully."""
    if not os.path.exists(filepath):
        print(f"WARNING: {name} file not found: {filepath}")
        return None

    try:
        gdf = gpd.read_file(filepath)
        print(f"Loaded {name}: {len(gdf)} features")
        return gdf
    except Exception as e:
        print(f"ERROR loading {name}: {e}")
        return None


def ensure_same_crs(gdf, target_crs, name):
    """Ensure GeoDataFrame is in the target CRS."""
    if gdf is None:
        return None

    if gdf.crs is None:
        print(f"WARNING: {name} has no CRS, assuming EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")

    if gdf.crs != target_crs:
        print(f"Reprojecting {name} from {gdf.crs} to {target_crs}")
        gdf = gdf.to_crs(target_crs)

    return gdf


def clip_to_boundary(gdf, boundary, name):
    """Clip a GeoDataFrame to a boundary using intersection overlay."""
    if gdf is None or boundary is None:
        return None

    try:
        # Use overlay with intersection to clip
        clipped = gpd.overlay(gdf, boundary[['geometry']], how='intersection')
        print(f"Clipped {name}: {len(gdf)} -> {len(clipped)} features")
        return clipped
    except Exception as e:
        print(f"ERROR clipping {name}: {e}")
        return None


def create_map(utility_gdf, oz_clipped, qct_clipped, streets_gdf):
    """Create the Folium map with all layers."""

    # Prepare all GeoDataFrames for JSON serialization
    utility_gdf = prepare_for_json(utility_gdf)
    oz_clipped = prepare_for_json(oz_clipped)
    qct_clipped = prepare_for_json(qct_clipped)
    streets_gdf = prepare_for_json(streets_gdf)

    # Calculate map center from utility boundary
    if utility_gdf is not None and len(utility_gdf) > 0:
        bounds = utility_gdf.total_bounds  # [minx, miny, maxx, maxy]
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
    else:
        # Default to Virginia center
        center_lat = 37.5
        center_lon = -79.0

    # Create base map with CartoDB Positron
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='CartoDB positron'
    )

    # Add utility territory layer (grey)
    if utility_gdf is not None:
        GeoJson(
            utility_gdf.to_json(),
            name="Utility Territory (Dominion)",
            style_function=lambda x: UTILITY_STYLE,
            tooltip=folium.GeoJsonTooltip(fields=[], aliases=[], labels=False)
        ).add_to(m)
        print("Added Utility Territory layer")

    # Add clipped Opportunity Zones layer (blue)
    if oz_clipped is not None and len(oz_clipped) > 0:
        GeoJson(
            oz_clipped.to_json(),
            name="Opportunity Zones (Clipped)",
            style_function=lambda x: OZ_STYLE,
            tooltip=folium.GeoJsonTooltip(
                fields=oz_clipped.columns[:3].tolist() if len(oz_clipped.columns) > 0 else [],
                aliases=[''] * min(3, len(oz_clipped.columns)),
                labels=True
            )
        ).add_to(m)
        print("Added Opportunity Zones layer")

    # Add clipped QCT layer (orange)
    if qct_clipped is not None and len(qct_clipped) > 0:
        GeoJson(
            qct_clipped.to_json(),
            name="HUD Qualified Census Tracts (Clipped)",
            style_function=lambda x: QCT_STYLE,
            tooltip=folium.GeoJsonTooltip(
                fields=qct_clipped.columns[:3].tolist() if len(qct_clipped.columns) > 0 else [],
                aliases=[''] * min(3, len(qct_clipped.columns)),
                labels=True
            )
        ).add_to(m)
        print("Added QCT layer")

    # Add extracted streets layer (green)
    if streets_gdf is not None and len(streets_gdf) > 0:
        GeoJson(
            streets_gdf.to_json(),
            name="Extracted Streets (VIPR)",
            style_function=lambda x: STREET_STYLE,
            tooltip=folium.GeoJsonTooltip(
                fields=streets_gdf.columns[:3].tolist() if len(streets_gdf.columns) > 0 else [],
                aliases=[''] * min(3, len(streets_gdf.columns)),
                labels=True
            )
        ).add_to(m)
        print("Added Streets layer")

    # Add layer control
    LayerControl(collapsed=False).add_to(m)

    return m


def main():
    """Main processing pipeline."""
    print("=" * 60)
    print("Market Map Generator - Dominion Energy Territory")
    print("=" * 60)

    # Step 1: Load all GeoJSON files
    print("\n[Step 1] Loading GeoJSON files...")
    utility_gdf = load_geojson(UTILITY_BOUNDARY, "Utility Boundary")
    oz_gdf = load_geojson(OPPORTUNITY_ZONES, "Opportunity Zones")
    qct_gdf = load_geojson(QCT_ZONES, "QCT Zones")
    streets_gdf = load_geojson(STREET_DATA, "Street Data")

    # Check if we have the minimum required data
    if utility_gdf is None:
        print("\nERROR: Utility boundary is required but not found.")
        print("Please ensure 'dominion_service_area.geojson' exists.")
        print("\nTo obtain this data:")
        print("  1. Download from utility company GIS portal, or")
        print("  2. Use HIFLD utility service territory data")
        return

    # Step 2: Ensure all layers use the same CRS
    print("\n[Step 2] Aligning coordinate reference systems...")
    target_crs = utility_gdf.crs if utility_gdf.crs else "EPSG:4326"

    oz_gdf = ensure_same_crs(oz_gdf, target_crs, "Opportunity Zones")
    qct_gdf = ensure_same_crs(qct_gdf, target_crs, "QCT Zones")
    streets_gdf = ensure_same_crs(streets_gdf, target_crs, "Streets")

    # Step 3: Clip zones to utility boundary
    print("\n[Step 3] Clipping zones to utility territory...")
    oz_clipped = clip_to_boundary(oz_gdf, utility_gdf, "Opportunity Zones")
    qct_clipped = clip_to_boundary(qct_gdf, utility_gdf, "QCT Zones")
    # Note: Streets are not clipped as they come pre-extracted from VIPR

    # Step 4: Create the map
    print("\n[Step 4] Generating interactive map...")
    m = create_map(utility_gdf, oz_clipped, qct_clipped, streets_gdf)

    # Step 5: Save the map
    print(f"\n[Step 5] Saving map to {OUTPUT_FILE}...")
    m.save(OUTPUT_FILE)
    print(f"SUCCESS: Map saved to {OUTPUT_FILE}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Utility Territory: {'Yes' if utility_gdf is not None else 'No'}")
    print(f"  Opportunity Zones: {len(oz_clipped) if oz_clipped is not None else 0} features clipped")
    print(f"  QCT Zones: {len(qct_clipped) if qct_clipped is not None else 0} features clipped")
    print(f"  Streets: {len(streets_gdf) if streets_gdf is not None else 0} features")
    print(f"\nOpen {OUTPUT_FILE} in your browser to verify the map.")


if __name__ == "__main__":
    main()
