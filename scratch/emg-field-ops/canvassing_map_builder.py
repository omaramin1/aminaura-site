#!/usr/bin/env python3
"""
EMG Field Ops - Canvassing Map Builder
Generates mobile-friendly maps for door-to-door solar sales reps.

Target: Find walkable neighborhoods where reps can close 10 deals/day
with 100k kWh total - focusing on LMI auto-qualify zones and high usage homes.

Layers:
- BLUE: LMI Auto-Qualify Zones (VIPR/QCT) - customers pre-qualify for state benefits
- GREEN: High Priority Streets - dense residential in blue zones
- ORANGE: High kWh Indicators - older homes, larger sq ft
"""

import geopandas as gpd
import folium
from folium import GeoJson, LayerControl, Marker, FeatureGroup
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
import pandas as pd
import requests
import json
import os

# =============================================================================
# CONFIGURATION
# =============================================================================

# Dominion Energy Virginia approximate service area (Richmond metro focus)
# These are key counties in Dominion territory with good solar potential
DOMINION_COUNTIES_FIPS = [
    "51041",  # Chesterfield
    "51087",  # Henrico
    "51760",  # Richmond City
    "51036",  # Charles City
    "51570",  # Colonial Heights
    "51670",  # Hopewell
    "51730",  # Petersburg
    "51149",  # Prince George
    "51183",  # Sussex
    "51590",  # Danville
    "51143",  # Pittsylvania
    "51550",  # Chesapeake
    "51710",  # Norfolk
    "51810",  # Virginia Beach
    "51740",  # Portsmouth
    "51650",  # Hampton
    "51700",  # Newport News
]

# Output
OUTPUT_FILE = "emg_canvassing_map.html"

# Styling for map layers
STYLES = {
    "lmi_zone": {
        "fillColor": "#2563eb",
        "color": "#1d4ed8",
        "weight": 2,
        "fillOpacity": 0.35,
    },
    "high_priority": {
        "fillColor": "#22c55e",
        "color": "#16a34a",
        "weight": 3,
        "fillOpacity": 0.5,
    },
    "vipr_zone": {
        "fillColor": "#3b82f6",
        "color": "#1e40af",
        "weight": 2,
        "fillOpacity": 0.4,
    },
    "territory": {
        "fillColor": "#6b7280",
        "color": "#374151",
        "weight": 1,
        "fillOpacity": 0.1,
    }
}

# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

def fetch_census_tracts_for_county(county_fips, state_fips="51"):
    """Fetch census tract boundaries from Census TIGERweb API."""
    url = (
        f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
        f"tigerWMS_Current/MapServer/8/query"
        f"?where=STATE%3D%27{state_fips}%27%20AND%20COUNTY%3D%27{county_fips[-3:]}%27"
        f"&outFields=GEOID,NAME,STATE,COUNTY,CENTLAT,CENTLON,AREALAND"
        f"&f=geojson"
    )

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return gpd.read_file(response.text)
    except Exception as e:
        print(f"  Error fetching tracts for {county_fips}: {e}")
    return None


def fetch_virginia_qct_list():
    """
    Return list of Virginia QCT GEOIDs for 2025.
    These are census tracts where 50%+ of households are below 60% AMI.
    Source: HUD QCT designations.
    """
    # Key Virginia QCTs in Dominion territory (partial list - high value areas)
    # Format: State(2) + County(3) + Tract(6)
    virginia_qcts = [
        # Richmond City area
        "51760010100", "51760010200", "51760010300", "51760010400",
        "51760010500", "51760010600", "51760010700", "51760010800",
        "51760020100", "51760020200", "51760020300", "51760020400",
        "51760030100", "51760030200", "51760030300",
        # Henrico County
        "51087200101", "51087200102", "51087200200", "51087200300",
        "51087200400", "51087200500", "51087200600",
        # Chesterfield County
        "51041100100", "51041100200", "51041100300", "51041100400",
        # Norfolk City
        "51710000100", "51710000200", "51710000300", "51710000400",
        "51710000500", "51710000600", "51710000700", "51710000800",
        "51710000900", "51710001000", "51710001100", "51710001200",
        # Virginia Beach
        "51810040100", "51810040200", "51810040300", "51810040400",
        # Hampton
        "51650010100", "51650010200", "51650010300", "51650010400",
        # Newport News
        "51700030100", "51700030200", "51700030300", "51700030400",
        # Petersburg
        "51730810100", "51730810200", "51730810300", "51730810400",
    ]
    return virginia_qcts


def load_vipr_zones(filepath="vipr_lmi_zones.geojson"):
    """Load VIPR LMI auto-qualify zones if available."""
    if os.path.exists(filepath):
        try:
            gdf = gpd.read_file(filepath)
            print(f"Loaded VIPR zones: {len(gdf)} features")
            return gdf
        except Exception as e:
            print(f"Error loading VIPR zones: {e}")
    return None


def prepare_for_json(gdf):
    """Convert timestamps for JSON serialization."""
    if gdf is None:
        return None
    gdf = gdf.copy()
    for col in gdf.columns:
        if col == 'geometry':
            continue
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
    return gdf


# =============================================================================
# MAP BUILDING FUNCTIONS
# =============================================================================

def create_canvassing_map(lmi_zones, vipr_zones=None, priority_streets=None):
    """
    Create mobile-friendly canvassing map.

    Features:
    - GPS location tracking for field reps
    - Fullscreen mode for mobile
    - Layer toggles
    - Street-level detail at zoom
    """

    # Center on Richmond/Hampton Roads (Dominion core territory)
    center_lat = 37.5
    center_lon = -77.4

    if lmi_zones is not None and len(lmi_zones) > 0:
        bounds = lmi_zones.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2

    # Create map with street-level base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles=None  # We'll add custom tiles
    )

    # Add multiple tile layers for field use
    folium.TileLayer(
        'OpenStreetMap',
        name='Street Map',
        control=True
    ).add_to(m)

    folium.TileLayer(
        'CartoDB positron',
        name='Light Map',
        control=True
    ).add_to(m)

    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        control=True
    ).add_to(m)

    # Add GPS locate control for field reps
    LocateControl(
        auto_start=False,
        strings={"title": "Find My Location", "popup": "You are here"}
    ).add_to(m)

    # Add fullscreen for mobile
    Fullscreen(
        position='topleft',
        title='Fullscreen',
        title_cancel='Exit Fullscreen'
    ).add_to(m)

    # === LAYER 1: VIPR LMI Auto-Qualify Zones (if available) ===
    if vipr_zones is not None and len(vipr_zones) > 0:
        vipr_zones = prepare_for_json(vipr_zones)
        vipr_group = FeatureGroup(name="🔵 VIPR Auto-Qualify Zones", show=True)
        GeoJson(
            vipr_zones.to_json(),
            style_function=lambda x: STYLES["vipr_zone"],
            tooltip=folium.GeoJsonTooltip(
                fields=['name'] if 'name' in vipr_zones.columns else [],
                aliases=['Zone:'],
                labels=True
            ),
            popup=folium.GeoJsonPopup(
                fields=vipr_zones.columns[:4].tolist(),
                aliases=[''] * 4,
                labels=True
            )
        ).add_to(vipr_group)
        vipr_group.add_to(m)
        print("Added VIPR zones layer")

    # === LAYER 2: HUD QCT LMI Zones (fallback/supplement) ===
    if lmi_zones is not None and len(lmi_zones) > 0:
        lmi_zones = prepare_for_json(lmi_zones)
        lmi_group = FeatureGroup(name="🔵 LMI Qualify Zones (QCT)", show=True)
        GeoJson(
            lmi_zones.to_json(),
            style_function=lambda x: STYLES["lmi_zone"],
            tooltip=folium.GeoJsonTooltip(
                fields=['NAME', 'GEOID'] if 'NAME' in lmi_zones.columns else [],
                aliases=['Tract:', 'GEOID:'],
                labels=True
            ),
            popup=folium.GeoJsonPopup(
                fields=['NAME', 'GEOID', 'COUNTY'] if 'NAME' in lmi_zones.columns else [],
                aliases=['Tract', 'GEOID', 'County'],
                labels=True
            )
        ).add_to(lmi_group)
        lmi_group.add_to(m)
        print("Added LMI zones layer")

    # === LAYER 3: Priority Streets (if available) ===
    if priority_streets is not None and len(priority_streets) > 0:
        priority_streets = prepare_for_json(priority_streets)
        street_group = FeatureGroup(name="🟢 Priority Streets", show=True)
        GeoJson(
            priority_streets.to_json(),
            style_function=lambda x: STYLES["high_priority"],
            tooltip=folium.GeoJsonTooltip(
                fields=priority_streets.columns[:2].tolist(),
                labels=True
            )
        ).add_to(street_group)
        street_group.add_to(m)
        print("Added priority streets layer")

    # Add layer control
    LayerControl(collapsed=False).add_to(m)

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                background-color: white; padding: 10px; border-radius: 5px;
                border: 2px solid #ccc; font-family: Arial; font-size: 12px;">
        <b>EMG Canvassing Map</b><br>
        <i style="background: #2563eb; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> LMI Auto-Qualify Zone<br>
        <i style="background: #22c55e; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Priority Streets<br>
        <hr style="margin: 5px 0;">
        <small>Goal: 10 deals / 100k kWh daily</small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("EMG Field Ops - Canvassing Map Builder")
    print("=" * 60)

    # Step 1: Try to load VIPR zones (primary source)
    print("\n[Step 1] Looking for VIPR LMI zones...")
    vipr_zones = load_vipr_zones("vipr_lmi_zones.geojson")

    if vipr_zones is None:
        print("  VIPR zones not found - will use HUD QCT data as fallback")

    # Step 2: Fetch census tract data for key Dominion counties
    print("\n[Step 2] Fetching census tract boundaries...")
    all_tracts = []
    qct_list = fetch_virginia_qct_list()

    for county_fips in DOMINION_COUNTIES_FIPS[:5]:  # Start with first 5 counties
        print(f"  Fetching county {county_fips}...")
        tracts = fetch_census_tracts_for_county(county_fips)
        if tracts is not None:
            all_tracts.append(tracts)

    if all_tracts:
        all_tracts_gdf = pd.concat(all_tracts, ignore_index=True)
        all_tracts_gdf = gpd.GeoDataFrame(all_tracts_gdf, geometry='geometry')
        print(f"  Total tracts fetched: {len(all_tracts_gdf)}")

        # Filter to only QCT tracts (LMI zones)
        lmi_zones = all_tracts_gdf[all_tracts_gdf['GEOID'].isin(qct_list)]
        print(f"  LMI qualifying tracts: {len(lmi_zones)}")
    else:
        print("  WARNING: Could not fetch tract data from Census API")
        lmi_zones = None

    # Step 3: Load priority streets if available
    print("\n[Step 3] Looking for priority streets...")
    priority_streets = None
    if os.path.exists("priority_streets.geojson"):
        try:
            priority_streets = gpd.read_file("priority_streets.geojson")
            print(f"  Loaded {len(priority_streets)} priority streets")
        except:
            pass

    if priority_streets is None:
        print("  No priority streets file found")

    # Step 4: Build the map
    print("\n[Step 4] Building canvassing map...")
    m = create_canvassing_map(lmi_zones, vipr_zones, priority_streets)

    # Step 5: Save
    print(f"\n[Step 5] Saving to {OUTPUT_FILE}...")
    m.save(OUTPUT_FILE)

    # Summary
    print("\n" + "=" * 60)
    print("CANVASSING MAP READY")
    print("=" * 60)
    print(f"  VIPR Zones: {'Yes' if vipr_zones is not None else 'No (waiting for data)'}")
    print(f"  LMI Zones (QCT): {len(lmi_zones) if lmi_zones is not None else 0} tracts")
    print(f"  Priority Streets: {len(priority_streets) if priority_streets is not None else 0}")
    print(f"\n  Open {OUTPUT_FILE} in browser or on mobile device")
    print("\n  Features:")
    print("  - GPS 'Find My Location' button")
    print("  - Fullscreen mode for mobile")
    print("  - Street/Satellite toggle")
    print("  - Layer on/off controls")


if __name__ == "__main__":
    main()
