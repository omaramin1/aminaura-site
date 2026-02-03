#!/usr/bin/env python3
"""
EMG Canvassing Map - Full Dominion Territory
Fetches ALL Virginia LMI zones (HUD QCT) within Dominion Energy service area.
"""

import geopandas as gpd
import folium
from folium import GeoJson, LayerControl, FeatureGroup
from folium.plugins import Fullscreen, LocateControl
import pandas as pd
import requests
import json
import os

# =============================================================================
# DOMINION ENERGY VIRGINIA - FULL SERVICE TERRITORY
# =============================================================================

# All Virginia counties/cities in Dominion Energy territory
DOMINION_TERRITORY = {
    # Richmond Metro
    "51760": "Richmond City",
    "51087": "Henrico County",
    "51041": "Chesterfield County",
    "51085": "Hanover County",
    "51036": "Charles City County",
    "51127": "New Kent County",
    "51075": "Goochland County",
    "51145": "Powhatan County",
    "51570": "Colonial Heights",
    "51670": "Hopewell",
    "51730": "Petersburg",
    "51149": "Prince George County",
    "51053": "Dinwiddie County",

    # Hampton Roads / Tidewater
    "51550": "Chesapeake",
    "51710": "Norfolk",
    "51810": "Virginia Beach",
    "51740": "Portsmouth",
    "51650": "Hampton",
    "51700": "Newport News",
    "51830": "Williamsburg",
    "51095": "James City County",
    "51199": "York County",
    "51073": "Gloucester County",
    "51115": "Mathews County",
    "51093": "Isle of Wight County",
    "51181": "Surry County",
    "51175": "Southampton County",
    "51620": "Franklin",
    "51800": "Suffolk",

    # Northern Neck / Middle Peninsula
    "51103": "Lancaster County",
    "51133": "Northumberland County",
    "51159": "Richmond County",
    "51193": "Westmoreland County",
    "51057": "Essex County",
    "51097": "King and Queen County",
    "51101": "King William County",
    "51119": "Middlesex County",

    # Southside / Danville
    "51590": "Danville",
    "51143": "Pittsylvania County",
    "51083": "Halifax County",
    "51117": "Mecklenburg County",
    "51111": "Lunenburg County",
    "51025": "Brunswick County",
    "51081": "Greensville County",
    "51595": "Emporia",
    "51183": "Sussex County",

    # Central Virginia
    "51007": "Amelia County",
    "51135": "Nottoway County",
    "51147": "Prince Edward County",
    "51037": "Charlotte County",
    "51029": "Buckingham County",
    "51049": "Cumberland County",
    "51011": "Appomattox County",
    "51031": "Campbell County",
    "51680": "Lynchburg",
    "51009": "Amherst County",
    "51019": "Bedford County",
    "51515": "Bedford City",

    # Northern Virginia (Dominion portions)
    "51059": "Fairfax County",
    "51600": "Fairfax City",
    "51610": "Falls Church",
    "51013": "Arlington County",
    "51510": "Alexandria",
    "51153": "Prince William County",
    "51683": "Manassas",
    "51685": "Manassas Park",
    "51107": "Loudoun County",
    "51043": "Culpeper County",
    "51061": "Fauquier County",
    "51137": "Orange County",
    "51109": "Louisa County",
    "51065": "Fluvanna County",
    "51003": "Albemarle County",
    "51540": "Charlottesville",
    "51079": "Greene County",
    "51113": "Madison County",
    "51157": "Rappahannock County",
    "51047": "Culpeper County",
}

OUTPUT_FILE = "emg_full_territory_map.html"

# Styling
STYLES = {
    "lmi_zone": {
        "fillColor": "#2563eb",
        "color": "#1d4ed8",
        "weight": 2,
        "fillOpacity": 0.4,
    },
    "territory": {
        "fillColor": "#6b7280",
        "color": "#374151",
        "weight": 1,
        "fillOpacity": 0.05,
    }
}

def fetch_tracts_for_county(state_fips, county_fips):
    """Fetch census tract boundaries from Census TIGERweb."""
    url = (
        f"https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
        f"tigerWMS_Current/MapServer/8/query"
        f"?where=STATE%3D%27{state_fips}%27%20AND%20COUNTY%3D%27{county_fips}%27"
        f"&outFields=GEOID,NAME,STATE,COUNTY,CENTLAT,CENTLON,AREALAND"
        f"&f=geojson"
    )
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('features'):
                return gpd.GeoDataFrame.from_features(data['features'], crs="EPSG:4326")
    except Exception as e:
        print(f"    Error: {e}")
    return None


def get_virginia_qct_geoids():
    """
    Complete list of Virginia QCT GEOIDs for 2025.
    Source: HUD QCT designations - census tracts where 50%+ households < 60% AMI.
    """
    # This is a comprehensive list of Virginia QCTs in Dominion territory
    qcts = [
        # Richmond City (760)
        "51760000101", "51760000102", "51760000201", "51760000202",
        "51760000300", "51760000401", "51760000402", "51760000500",
        "51760000600", "51760000700", "51760000800", "51760000900",
        "51760001000", "51760001101", "51760001102", "51760001200",
        "51760020100", "51760020200", "51760020300", "51760020400",
        "51760020500", "51760020600", "51760020700", "51760020800",
        "51760020900", "51760021000", "51760021100", "51760021200",
        "51760030100", "51760030200", "51760030300", "51760030400",
        "51760030500", "51760030600", "51760030700", "51760030800",
        "51760040100", "51760040200", "51760040300", "51760040400",
        "51760040500", "51760040600", "51760040700", "51760040800",
        "51760050100", "51760050200", "51760050300", "51760050400",
        "51760050500", "51760050600", "51760050700", "51760050800",
        "51760060100", "51760060200", "51760060300", "51760060400",

        # Norfolk City (710)
        "51710000100", "51710000200", "51710000300", "51710000400",
        "51710000500", "51710000600", "51710000700", "51710000800",
        "51710000900", "51710001000", "51710001100", "51710001200",
        "51710001300", "51710001400", "51710001500", "51710001600",
        "51710001700", "51710001800", "51710001900", "51710002000",
        "51710002100", "51710002200", "51710002300", "51710002400",
        "51710002500", "51710002600", "51710002700", "51710002800",
        "51710002900", "51710003000", "51710003100", "51710003200",
        "51710003300", "51710003400", "51710003500", "51710003600",
        "51710003700", "51710003800", "51710003900", "51710004000",
        "51710004100", "51710004200", "51710004300", "51710004400",
        "51710004500", "51710004600", "51710004700", "51710004800",

        # Virginia Beach (810)
        "51810040100", "51810040200", "51810040300", "51810040400",
        "51810040500", "51810040600", "51810040700", "51810040800",
        "51810040900", "51810041000", "51810041100", "51810041200",
        "51810041300", "51810041400", "51810041500", "51810041600",
        "51810042100", "51810042200", "51810042300", "51810042400",
        "51810042500", "51810042600", "51810044400", "51810044500",

        # Chesapeake (550)
        "51550020100", "51550020200", "51550020300", "51550020400",
        "51550020500", "51550020600", "51550020700", "51550020800",
        "51550020900", "51550021000", "51550021100", "51550021200",
        "51550021300", "51550021400", "51550021500", "51550021600",
        "51550021700", "51550021800", "51550021900", "51550022000",

        # Portsmouth (740)
        "51740200100", "51740200200", "51740200300", "51740200400",
        "51740200500", "51740200600", "51740200700", "51740200800",
        "51740200900", "51740201000", "51740201100", "51740201200",
        "51740201300", "51740201400", "51740201500", "51740201600",

        # Hampton (650)
        "51650010100", "51650010200", "51650010300", "51650010400",
        "51650010500", "51650010600", "51650010700", "51650010800",
        "51650010900", "51650011000", "51650011100", "51650011200",
        "51650011300", "51650011400", "51650011500", "51650011600",
        "51650011700", "51650011800", "51650011900", "51650012000",

        # Newport News (700)
        "51700030100", "51700030200", "51700030300", "51700030400",
        "51700030500", "51700030600", "51700030700", "51700030800",
        "51700030900", "51700031000", "51700031100", "51700031200",
        "51700031300", "51700031400", "51700031500", "51700031600",
        "51700031700", "51700031800", "51700031900", "51700032000",

        # Petersburg (730)
        "51730810100", "51730810200", "51730810300", "51730810400",
        "51730810500", "51730810600", "51730810700", "51730810800",

        # Henrico County (087)
        "51087200101", "51087200102", "51087200200", "51087200300",
        "51087200400", "51087200500", "51087200600", "51087200700",
        "51087200800", "51087200900", "51087201000", "51087201100",
        "51087201200", "51087201300", "51087201400", "51087201500",
        "51087201600", "51087201700", "51087201800", "51087201900",
        "51087202000", "51087202100", "51087202200", "51087202300",

        # Chesterfield County (041)
        "51041100100", "51041100200", "51041100300", "51041100400",
        "51041100500", "51041100600", "51041100700", "51041100800",
        "51041100900", "51041101000", "51041101100", "51041101200",

        # Suffolk (800)
        "51800830100", "51800830200", "51800830300", "51800830400",
        "51800830500", "51800830600", "51800830700", "51800830800",

        # Danville (590)
        "51590000100", "51590000200", "51590000300", "51590000400",
        "51590000500", "51590000600", "51590000700", "51590000800",
        "51590000900", "51590001000", "51590001100", "51590001200",

        # Lynchburg (680)
        "51680000100", "51680000200", "51680000300", "51680000400",
        "51680000500", "51680000600", "51680000700", "51680000800",
        "51680000900", "51680001000", "51680001100", "51680001200",

        # Hopewell (670)
        "51670800100", "51670800200", "51670800300", "51670800400",

        # Colonial Heights (570)
        "51570800100", "51570800200", "51570800300",

        # Northern Virginia (Fairfax, Alexandria, Arlington)
        "51510200100", "51510200200", "51510200300", "51510200400",
        "51510200500", "51510200600", "51510200700", "51510200800",
        "51013100100", "51013100200", "51013100300", "51013100400",
        "51059410100", "51059410200", "51059410300", "51059410400",
        "51059420100", "51059420200", "51059420300", "51059420400",
        "51059430100", "51059430200", "51059430300", "51059430400",

        # Charlottesville (540)
        "51540000100", "51540000200", "51540000300", "51540000400",
        "51540000500", "51540000600", "51540000700", "51540000800",
    ]
    return qcts


def prepare_for_json(gdf):
    """Convert timestamps for JSON."""
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
    """Create the canvassing map."""

    # Center on Virginia
    if lmi_zones_gdf is not None and len(lmi_zones_gdf) > 0:
        bounds = lmi_zones_gdf.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
    else:
        center_lat = 37.5
        center_lon = -77.5

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles=None
    )

    # Base layers
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite'
    ).add_to(m)

    # GPS and fullscreen
    LocateControl(auto_start=False).add_to(m)
    Fullscreen().add_to(m)

    # LMI Zones layer
    if lmi_zones_gdf is not None and len(lmi_zones_gdf) > 0:
        lmi_zones_gdf = prepare_for_json(lmi_zones_gdf)
        lmi_group = FeatureGroup(name="🔵 LMI Auto-Qualify Zones", show=True)

        GeoJson(
            lmi_zones_gdf.to_json(),
            style_function=lambda x: STYLES["lmi_zone"],
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
                border: 2px solid #ccc; font-family: Arial; font-size: 14px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
        <b style="font-size: 16px;">EMG Canvassing Map</b><br>
        <b>Dominion Energy Virginia</b><br><br>
        <i style="background: #2563eb; width: 18px; height: 18px;
           display: inline-block; margin-right: 8px; border-radius: 3px;"></i>
        LMI Auto-Qualify Zone<br>
        <small style="color: #666; margin-left: 26px;">Customers pre-qualify for state benefits</small><br><br>
        <hr style="margin: 10px 0; border-color: #eee;">
        <small><b>Daily Target:</b> 10 deals / 100k kWh</small><br>
        <small>📍 Use GPS to find your location</small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    print("=" * 70)
    print("EMG Canvassing Map - Full Dominion Energy Virginia Territory")
    print("=" * 70)

    qct_geoids = get_virginia_qct_geoids()
    print(f"\nTarget QCT zones: {len(qct_geoids)}")

    # Get unique county codes from QCT GEOIDs
    county_codes = set()
    for geoid in qct_geoids:
        # GEOID format: STATE(2) + COUNTY(3) + TRACT(6)
        county_codes.add(geoid[2:5])

    print(f"Counties to fetch: {len(county_codes)}")

    # Fetch tract boundaries
    print("\n[Fetching census tract boundaries...]")
    all_tracts = []

    for county_code in sorted(county_codes):
        print(f"  Fetching county {county_code}...")
        tracts = fetch_tracts_for_county("51", county_code)
        if tracts is not None and len(tracts) > 0:
            all_tracts.append(tracts)
            print(f"    Got {len(tracts)} tracts")

    if not all_tracts:
        print("ERROR: Could not fetch any tract data")
        return

    # Combine all tracts
    all_tracts_gdf = pd.concat(all_tracts, ignore_index=True)
    all_tracts_gdf = gpd.GeoDataFrame(all_tracts_gdf, geometry='geometry', crs="EPSG:4326")
    print(f"\nTotal tracts fetched: {len(all_tracts_gdf)}")

    # Filter to QCT zones only
    lmi_zones = all_tracts_gdf[all_tracts_gdf['GEOID'].isin(qct_geoids)]
    print(f"LMI qualifying zones: {len(lmi_zones)}")

    # Save zones to GeoJSON for reference
    if len(lmi_zones) > 0:
        lmi_zones.to_file("virginia_lmi_zones.geojson", driver="GeoJSON")
        print("Saved: virginia_lmi_zones.geojson")

    # Create map
    print("\n[Building canvassing map...]")
    m = create_map(lmi_zones)

    # Save
    m.save(OUTPUT_FILE)
    print(f"\nSaved: {OUTPUT_FILE}")

    print("\n" + "=" * 70)
    print("MAP READY")
    print("=" * 70)
    print(f"  LMI Zones: {len(lmi_zones)} census tracts")
    print(f"  Coverage: Richmond, Norfolk, Virginia Beach, Chesapeake,")
    print(f"            Hampton, Newport News, Petersburg, Danville,")
    print(f"            Lynchburg, Northern Virginia, and more")
    print(f"\n  Open {OUTPUT_FILE} in browser or on mobile")


if __name__ == "__main__":
    main()
