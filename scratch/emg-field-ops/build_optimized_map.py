#!/usr/bin/env python3
"""
EMG Canvassing Map - Optimized/Light Version
Simplifies geometry to reduce file size for mobile browsers.
"""

import geopandas as gpd
import folium
from folium import GeoJson, LayerControl, FeatureGroup
from folium.plugins import Fullscreen, LocateControl, MarkerCluster
import pandas as pd
import json

INPUT_FILE = "vipr_lmi_zones_complete.geojson"
OUTPUT_FILE = "emg_map_optimized.html"

STYLE_LMI = {
    "fillColor": "#2563eb",
    "color": "#1d4ed8",
    "weight": 1,
    "fillOpacity": 0.35,
}


def simplify_geometry(gdf, tolerance=0.001):
    """Simplify polygon geometry to reduce file size."""
    gdf = gdf.copy()
    gdf['geometry'] = gdf['geometry'].simplify(tolerance, preserve_topology=True)
    return gdf


def prepare_for_json(gdf):
    if gdf is None:
        return None
    gdf = gdf.copy()
    for col in gdf.columns:
        if col == 'geometry':
            continue
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
    return gdf


def main():
    print("Loading zones...")
    zones = gpd.read_file(INPUT_FILE)
    print(f"Loaded {len(zones)} zones")

    # Calculate original size
    original_json = zones.to_json()
    print(f"Original size: {len(original_json) / 1024 / 1024:.1f} MB")

    # Simplify geometry
    print("Simplifying geometry...")
    zones_simple = simplify_geometry(zones, tolerance=0.002)

    # Check new size
    simple_json = zones_simple.to_json()
    print(f"Simplified size: {len(simple_json) / 1024 / 1024:.1f} MB")

    # Remove unnecessary columns to reduce size further
    keep_cols = ['geometry', 'NAME', 'GEOID', 'COUNTY_NAME']
    zones_simple = zones_simple[[c for c in keep_cols if c in zones_simple.columns]]

    final_json = zones_simple.to_json()
    print(f"Final size: {len(final_json) / 1024 / 1024:.1f} MB")

    # Build map
    print("Building map...")
    bounds = zones_simple.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='CartoDB positron',
        prefer_canvas=True  # Better performance
    )

    # Add other tile options
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite'
    ).add_to(m)

    # GPS and fullscreen
    LocateControl(auto_start=False).add_to(m)
    Fullscreen().add_to(m)

    # Add zones
    zones_simple = prepare_for_json(zones_simple)

    GeoJson(
        zones_simple.to_json(),
        name="🔵 LMI Auto-Qualify Zones",
        style_function=lambda x: STYLE_LMI,
        tooltip=folium.GeoJsonTooltip(
            fields=['NAME'] if 'NAME' in zones_simple.columns else [],
            aliases=['Tract:'],
            labels=True
        )
    ).add_to(m)

    LayerControl().add_to(m)

    # Compact legend
    legend = '''
    <div style="position:fixed;bottom:30px;left:10px;z-index:1000;
                background:white;padding:10px;border-radius:5px;
                border:1px solid #ccc;font:12px Arial;">
        <b>EMG Canvassing</b><br>
        <span style="color:#2563eb;">■</span> LMI Zone (1,760 total)<br>
        <small>📍GPS | 📱Fullscreen</small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend))

    # Save
    print(f"Saving to {OUTPUT_FILE}...")
    m.save(OUTPUT_FILE)

    import os
    size = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
    print(f"\nDone! File size: {size:.1f} MB")


if __name__ == "__main__":
    main()
