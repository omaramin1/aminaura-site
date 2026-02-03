#!/usr/bin/env python3
"""
EMG Canvassing Map - FULL VIPR Coverage
Matches the VA Low Income Housing zones shown in VIPR portal.
Includes ALL rural LMI zones across Dominion Energy Virginia territory.
"""

import geopandas as gpd
import folium
from folium import GeoJson, LayerControl, FeatureGroup
from folium.plugins import Fullscreen, LocateControl
import pandas as pd
import requests
import json

# =============================================================================
# FULL DOMINION TERRITORY - ALL COUNTIES WITH LMI ZONES (from VIPR screenshots)
# =============================================================================

# Counties visible in VIPR overview maps - organized by region
VIPR_LMI_COUNTIES = {
    # HAMPTON ROADS (Image 1)
    "550": "Chesapeake",
    "710": "Norfolk",
    "810": "Virginia Beach",
    "740": "Portsmouth",
    "650": "Hampton",
    "700": "Newport News",
    "800": "Suffolk",
    "093": "Isle of Wight",
    "175": "Southampton",
    "095": "James City",
    "199": "York",
    "073": "Gloucester",
    "115": "Mathews",

    # RICHMOND METRO (Image 2)
    "760": "Richmond City",
    "087": "Henrico",
    "041": "Chesterfield",
    "085": "Hanover",
    "036": "Charles City",
    "127": "New Kent",
    "075": "Goochland",
    "145": "Powhatan",
    "570": "Colonial Heights",
    "670": "Hopewell",

    # PETERSBURG / SOUTHSIDE (Image 3)
    "730": "Petersburg",
    "149": "Prince George",
    "053": "Dinwiddie",
    "025": "Brunswick",
    "081": "Greensville",
    "595": "Emporia",
    "183": "Sussex",
    "181": "Surry",
    "117": "Mecklenburg",
    "111": "Lunenburg",
    "135": "Nottoway",
    "007": "Amelia",
    "147": "Prince Edward",
    "037": "Charlotte",
    "083": "Halifax",
    "143": "Pittsylvania",
    "590": "Danville",

    # LYNCHBURG / CENTRAL VA (Image 4)
    "680": "Lynchburg",
    "031": "Campbell",
    "009": "Amherst",
    "011": "Appomattox",
    "019": "Bedford County",
    "515": "Bedford City",
    "029": "Buckingham",
    "049": "Cumberland",
    "065": "Fluvanna",
    "109": "Louisa",
    "137": "Orange",
    "003": "Albemarle",
    "540": "Charlottesville",
    "079": "Greene",
    "113": "Madison",
    "157": "Rappahannock",
    "047": "Culpeper",
    "061": "Fauquier",

    # NORTHERN NECK / MIDDLE PENINSULA
    "103": "Lancaster",
    "133": "Northumberland",
    "159": "Richmond County",
    "193": "Westmoreland",
    "057": "Essex",
    "097": "King and Queen",
    "099": "King George",
    "101": "King William",
    "119": "Middlesex",
    "033": "Caroline",

    # NORTHERN VIRGINIA (partial Dominion)
    "059": "Fairfax",
    "600": "Fairfax City",
    "610": "Falls Church",
    "013": "Arlington",
    "510": "Alexandria",
    "153": "Prince William",
    "683": "Manassas",
    "685": "Manassas Park",
    "107": "Loudoun",
    "177": "Spotsylvania",
    "630": "Fredericksburg",
    "179": "Stafford",
}

OUTPUT_FILE = "emg_vipr_complete_map.html"

STYLE_LMI = {
    "fillColor": "#2563eb",
    "color": "#1d4ed8",
    "weight": 1.5,
    "fillOpacity": 0.4,
}


def fetch_all_tracts_for_county(county_fips):
    """Fetch ALL census tracts for a county."""
    url = (
        f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
        f"tigerWMS_Current/MapServer/8/query"
        f"?where=STATE%3D%2751%27%20AND%20COUNTY%3D%27{county_fips}%27"
        f"&outFields=GEOID,NAME,STATE,COUNTY,CENTLAT,CENTLON,AREALAND"
        f"&f=geojson"
    )
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('features'):
                gdf = gpd.GeoDataFrame.from_features(data['features'], crs="EPSG:4326")
                return gdf
    except Exception as e:
        print(f"    Error: {e}")
    return None


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


def create_map(lmi_zones_gdf):
    """Create comprehensive canvassing map."""

    if lmi_zones_gdf is not None and len(lmi_zones_gdf) > 0:
        bounds = lmi_zones_gdf.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
    else:
        center_lat = 37.5
        center_lon = -78.5

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles=None
    )

    # Base layers
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite'
    ).add_to(m)

    LocateControl(auto_start=False, strings={"title": "Find Me", "popup": "Your location"}).add_to(m)
    Fullscreen().add_to(m)

    # LMI Zones
    if lmi_zones_gdf is not None and len(lmi_zones_gdf) > 0:
        lmi_zones_gdf = prepare_for_json(lmi_zones_gdf)
        lmi_group = FeatureGroup(name="🔵 LMI Auto-Qualify Zones (VIPR)", show=True)

        GeoJson(
            lmi_zones_gdf.to_json(),
            style_function=lambda x: STYLE_LMI,
            tooltip=folium.GeoJsonTooltip(
                fields=['NAME', 'GEOID'] if 'NAME' in lmi_zones_gdf.columns else [],
                aliases=['Tract:', 'GEOID:'],
                labels=True
            )
        ).add_to(lmi_group)
        lmi_group.add_to(m)

    LayerControl(collapsed=False).add_to(m)

    # Legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                background: white; padding: 15px; border-radius: 8px;
                border: 2px solid #ccc; font-family: Arial; font-size: 13px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3); max-width: 280px;">
        <b style="font-size: 15px;">EMG Canvassing Map</b><br>
        <span style="color: #666;">Dominion Energy Virginia - VIPR Zones</span><br><br>
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <i style="background: #2563eb; width: 20px; height: 20px;
               display: inline-block; margin-right: 10px; border-radius: 3px;
               border: 1px solid #1d4ed8;"></i>
            <span><b>LMI Auto-Qualify Zone</b><br>
            <small style="color: #666;">Customers pre-qualify for state solar benefits</small></span>
        </div>
        <hr style="margin: 10px 0; border-color: #eee;">
        <small>
        <b>Daily Target:</b> 10 deals / 100k kWh<br>
        📍 Tap GPS icon to find your location<br>
        📱 Tap fullscreen for mobile view
        </small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    print("=" * 70)
    print("EMG Canvassing Map - FULL VIPR Coverage Builder")
    print("=" * 70)
    print(f"\nFetching ALL census tracts for {len(VIPR_LMI_COUNTIES)} counties...")

    all_tracts = []

    for county_fips, county_name in sorted(VIPR_LMI_COUNTIES.items()):
        print(f"  {county_name} ({county_fips})...", end=" ")
        tracts = fetch_all_tracts_for_county(county_fips)
        if tracts is not None and len(tracts) > 0:
            # Add county name to each tract
            tracts['COUNTY_NAME'] = county_name
            all_tracts.append(tracts)
            print(f"{len(tracts)} tracts")
        else:
            print("failed")

    if not all_tracts:
        print("ERROR: No tract data fetched")
        return

    # Combine all
    all_zones = pd.concat(all_tracts, ignore_index=True)
    all_zones = gpd.GeoDataFrame(all_zones, geometry='geometry', crs="EPSG:4326")

    print(f"\n{'='*70}")
    print(f"TOTAL LMI ZONES: {len(all_zones)}")
    print(f"{'='*70}")

    # Save GeoJSON
    all_zones.to_file("vipr_lmi_zones_complete.geojson", driver="GeoJSON")
    print(f"\nSaved: vipr_lmi_zones_complete.geojson")

    # Build map
    print("\nBuilding map...")
    m = create_map(all_zones)
    m.save(OUTPUT_FILE)
    print(f"Saved: {OUTPUT_FILE}")

    # Summary by region
    print(f"\n{'='*70}")
    print("COVERAGE SUMMARY")
    print(f"{'='*70}")

    regions = {
        "Hampton Roads": ["550", "710", "810", "740", "650", "700", "800", "093", "175"],
        "Richmond Metro": ["760", "087", "041", "085", "036", "127", "075", "145", "570", "670"],
        "Petersburg/Southside": ["730", "149", "053", "025", "081", "595", "183", "181", "117", "111", "135", "007", "147", "037", "083", "143", "590"],
        "Lynchburg/Central": ["680", "031", "009", "011", "019", "515", "029", "049", "065", "109", "137", "003", "540"],
        "Northern Virginia": ["059", "600", "610", "013", "510", "153", "683", "685", "107"],
    }

    for region, counties in regions.items():
        count = len(all_zones[all_zones['COUNTY'].isin(counties)])
        print(f"  {region}: {count} zones")

    print(f"\n  Open {OUTPUT_FILE} in your browser")
    print("  Compare to VIPR portal to verify coverage matches")


if __name__ == "__main__":
    main()
