#!/usr/bin/env python3
"""
EMG Canvassing Maps - Regional Split (Full Detail)
Creates separate detailed maps for each region that will load in browsers.
"""

import geopandas as gpd
import folium
from folium import GeoJson, LayerControl, FeatureGroup
from folium.plugins import Fullscreen, LocateControl
import pandas as pd
import os

INPUT_FILE = "vipr_lmi_zones_complete.geojson"

# Define regions by county FIPS codes
REGIONS = {
    "hampton_roads": {
        "name": "Hampton Roads",
        "counties": ["550", "710", "810", "740", "650", "700", "800", "093", "175", "095", "199", "073", "115"],
        "center": [36.85, -76.3],
        "zoom": 10
    },
    "richmond": {
        "name": "Richmond Metro",
        "counties": ["760", "087", "041", "085", "036", "127", "075", "145", "570", "670"],
        "center": [37.54, -77.46],
        "zoom": 10
    },
    "petersburg_southside": {
        "name": "Petersburg & Southside",
        "counties": ["730", "149", "053", "025", "081", "595", "183", "181", "117", "111", "135", "007", "147", "037", "083", "143", "590"],
        "center": [36.9, -77.8],
        "zoom": 9
    },
    "lynchburg_central": {
        "name": "Lynchburg & Central VA",
        "counties": ["680", "031", "009", "011", "019", "515", "029", "049", "065", "109", "137", "003", "540", "079", "113", "157", "047", "061"],
        "center": [37.4, -79.1],
        "zoom": 9
    },
    "northern_va": {
        "name": "Northern Virginia",
        "counties": ["059", "600", "610", "013", "510", "153", "683", "685", "107", "177", "630", "179", "033", "099"],
        "center": [38.85, -77.3],
        "zoom": 10
    },
    "northern_neck": {
        "name": "Northern Neck & Middle Peninsula",
        "counties": ["103", "133", "159", "193", "057", "097", "101", "119"],
        "center": [37.7, -76.6],
        "zoom": 10
    }
}

STYLE_LMI = {
    "fillColor": "#2563eb",
    "color": "#1d4ed8",
    "weight": 2,
    "fillOpacity": 0.4,
}


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


def create_regional_map(zones_gdf, region_key, region_info):
    """Create a detailed map for one region."""

    center = region_info["center"]
    zoom = region_info["zoom"]
    name = region_info["name"]

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='CartoDB positron'
    )

    # Tile layers
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite'
    ).add_to(m)

    # Controls
    LocateControl(auto_start=False, strings={"title": "Find Me"}).add_to(m)
    Fullscreen().add_to(m)

    # Add zones with full detail
    zones_gdf = prepare_for_json(zones_gdf)

    tooltip_fields = []
    tooltip_aliases = []
    if 'NAME' in zones_gdf.columns:
        tooltip_fields.append('NAME')
        tooltip_aliases.append('Tract:')
    if 'COUNTY_NAME' in zones_gdf.columns:
        tooltip_fields.append('COUNTY_NAME')
        tooltip_aliases.append('County:')
    if 'GEOID' in zones_gdf.columns:
        tooltip_fields.append('GEOID')
        tooltip_aliases.append('GEOID:')

    GeoJson(
        zones_gdf.to_json(),
        name=f"🔵 LMI Zones - {name}",
        style_function=lambda x: STYLE_LMI,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            labels=True
        )
    ).add_to(m)

    LayerControl(collapsed=False).add_to(m)

    # Legend with region info
    legend = f'''
    <div style="position:fixed;bottom:30px;left:10px;z-index:1000;
                background:white;padding:12px;border-radius:8px;
                border:2px solid #2563eb;font:13px Arial;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
        <b style="font-size:15px;">EMG Canvassing Map</b><br>
        <b style="color:#2563eb;">{name}</b><br><br>
        <span style="background:#2563eb;color:white;padding:2px 6px;border-radius:3px;">
            {len(zones_gdf)} LMI Zones
        </span><br><br>
        <small>
        📍 GPS locate available<br>
        📱 Fullscreen for mobile<br>
        🗺️ Toggle Street/Satellite<br><br>
        <b>Target:</b> 10 deals / 100k kWh daily
        </small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend))

    return m


def main():
    print("=" * 60)
    print("EMG Regional Maps Builder (Full Detail)")
    print("=" * 60)

    print(f"\nLoading zones from {INPUT_FILE}...")
    all_zones = gpd.read_file(INPUT_FILE)
    print(f"Loaded {len(all_zones)} total zones")

    # Create output directory
    os.makedirs("regional_maps", exist_ok=True)

    # Build each regional map
    for region_key, region_info in REGIONS.items():
        print(f"\n[{region_info['name']}]")

        # Filter zones for this region
        regional_zones = all_zones[all_zones['COUNTY'].isin(region_info['counties'])]
        print(f"  Zones: {len(regional_zones)}")

        if len(regional_zones) == 0:
            print("  Skipping - no zones")
            continue

        # Build map
        m = create_regional_map(regional_zones, region_key, region_info)

        # Save
        output_path = f"regional_maps/emg_map_{region_key}.html"
        m.save(output_path)

        size = os.path.getsize(output_path) / 1024 / 1024
        print(f"  Saved: {output_path} ({size:.1f} MB)")

    # Create index page
    index_html = '''<!DOCTYPE html>
<html>
<head>
    <title>EMG Canvassing Maps - Dominion VA</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        h1 { color: #1d4ed8; }
        .region { display: block; padding: 15px; margin: 10px 0; background: #f0f7ff;
                  border-radius: 8px; text-decoration: none; color: #333;
                  border-left: 4px solid #2563eb; }
        .region:hover { background: #e0efff; }
        .region b { color: #1d4ed8; font-size: 18px; }
        .region small { color: #666; }
    </style>
</head>
<body>
    <h1>🔵 EMG Canvassing Maps</h1>
    <p>Dominion Energy Virginia - LMI Auto-Qualify Zones</p>
    <p><b>Select your region:</b></p>

    <a class="region" href="emg_map_hampton_roads.html">
        <b>Hampton Roads</b><br>
        <small>Norfolk, Virginia Beach, Chesapeake, Hampton, Newport News, Suffolk</small>
    </a>

    <a class="region" href="emg_map_richmond.html">
        <b>Richmond Metro</b><br>
        <small>Richmond, Henrico, Chesterfield, Hanover, Colonial Heights, Hopewell</small>
    </a>

    <a class="region" href="emg_map_petersburg_southside.html">
        <b>Petersburg & Southside</b><br>
        <small>Petersburg, Danville, Halifax, Mecklenburg, Brunswick, Sussex</small>
    </a>

    <a class="region" href="emg_map_lynchburg_central.html">
        <b>Lynchburg & Central VA</b><br>
        <small>Lynchburg, Bedford, Campbell, Charlottesville, Albemarle, Orange</small>
    </a>

    <a class="region" href="emg_map_northern_va.html">
        <b>Northern Virginia</b><br>
        <small>Fairfax, Arlington, Alexandria, Prince William, Loudoun, Fredericksburg</small>
    </a>

    <a class="region" href="emg_map_northern_neck.html">
        <b>Northern Neck & Middle Peninsula</b><br>
        <small>Lancaster, Northumberland, Westmoreland, Essex, King William</small>
    </a>

    <hr style="margin: 30px 0;">
    <p><small>
        <b>Daily Target:</b> 10 deals / 100k kWh<br>
        All maps include GPS locate and fullscreen mode for mobile.
    </small></p>
</body>
</html>'''

    with open("regional_maps/index.html", "w") as f:
        f.write(index_html)
    print("\nSaved: regional_maps/index.html")

    print("\n" + "=" * 60)
    print("DONE! Regional maps created in regional_maps/ folder")
    print("=" * 60)
    print("\nOpen regional_maps/index.html to select a region")


if __name__ == "__main__":
    main()
