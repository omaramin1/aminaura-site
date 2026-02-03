#!/usr/bin/env python3
"""
VIPR Portal Zone Extractor
Logs into the VIPR portal and extracts LMI auto-qualify zone data.
"""

import requests
import json
import re
import os

# Portal configuration
PORTAL_URL = "https://portal.viprweb.com"
EMAIL = "carli@cmwmarketingsolutions.com"
PASSWORD = "Solar2025!Solar2025!V"

OUTPUT_FILE = "vipr_lmi_zones.geojson"


def extract_vipr_zones():
    """Attempt to extract zone data from VIPR portal."""

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    print("=" * 60)
    print("VIPR Portal Zone Extractor")
    print("=" * 60)

    # Step 1: Get the initial page to find login endpoints
    print("\n[Step 1] Fetching portal homepage...")
    try:
        resp = session.get(PORTAL_URL, timeout=30)
        print(f"  Status: {resp.status_code}")

        # Look for API endpoints in the page
        api_patterns = [
            r'api["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'(\/api\/[^\s"\'<>]+)',
            r'(\/v\d\/[^\s"\'<>]+)',
            r'baseUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, resp.text)
            if matches:
                print(f"  Found potential API: {matches[:3]}")

    except Exception as e:
        print(f"  Error: {e}")
        return None

    # Step 2: Try to find login endpoint
    print("\n[Step 2] Looking for authentication endpoints...")

    # Common API patterns for login
    login_endpoints = [
        f"{PORTAL_URL}/api/login",
        f"{PORTAL_URL}/api/auth/login",
        f"{PORTAL_URL}/login",
        f"{PORTAL_URL}/api/v1/login",
        f"{PORTAL_URL}/api/authenticate",
    ]

    login_payloads = [
        {"email": EMAIL, "password": PASSWORD},
        {"username": EMAIL, "password": PASSWORD},
        {"Email": EMAIL, "Password": PASSWORD},
    ]

    for endpoint in login_endpoints:
        for payload in login_payloads:
            try:
                print(f"  Trying: {endpoint}")
                resp = session.post(endpoint, json=payload, timeout=10)
                print(f"    Status: {resp.status_code}")

                if resp.status_code == 200:
                    print(f"    Response: {resp.text[:200]}")
                    if "token" in resp.text.lower() or "success" in resp.text.lower():
                        print("  LOGIN SUCCESS!")
                        break
            except Exception as e:
                print(f"    Error: {e}")
                continue

    # Step 3: Try to access map data endpoints
    print("\n[Step 3] Looking for map/zone data endpoints...")

    map_endpoints = [
        f"{PORTAL_URL}/api/map",
        f"{PORTAL_URL}/api/zones",
        f"{PORTAL_URL}/api/lmi-zones",
        f"{PORTAL_URL}/api/sales-map",
        f"{PORTAL_URL}/api/v1/map/layers",
        f"{PORTAL_URL}/api/geojson",
        f"{PORTAL_URL}/map/data",
        f"{PORTAL_URL}/Sales_Map/data",
    ]

    for endpoint in map_endpoints:
        try:
            print(f"  Trying: {endpoint}")
            resp = session.get(endpoint, timeout=10)
            print(f"    Status: {resp.status_code}")

            if resp.status_code == 200:
                # Check if it's GeoJSON
                try:
                    data = resp.json()
                    if "features" in data or "type" in data:
                        print("    Found GeoJSON data!")
                        return data
                except:
                    pass
        except Exception as e:
            print(f"    Error: {e}")
            continue

    # Step 4: Check for ArcGIS/MapBox endpoints
    print("\n[Step 4] Checking for mapping service endpoints...")

    # VIPR might use ArcGIS or Mapbox - check for service URLs
    try:
        resp = session.get(f"{PORTAL_URL}/#Sales_Map", timeout=10)

        # Look for tile/feature service URLs
        arcgis_pattern = r'(https?://[^\s"\'<>]*arcgis[^\s"\'<>]*)'
        mapbox_pattern = r'(https?://[^\s"\'<>]*mapbox[^\s"\'<>]*)'
        geojson_pattern = r'(https?://[^\s"\'<>]*\.geojson[^\s"\'<>]*)'

        for pattern, name in [(arcgis_pattern, "ArcGIS"),
                               (mapbox_pattern, "MapBox"),
                               (geojson_pattern, "GeoJSON")]:
            matches = re.findall(pattern, resp.text)
            if matches:
                print(f"  Found {name} URLs: {matches[:3]}")

    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("EXTRACTION NOTES")
    print("=" * 60)
    print("""
The VIPR portal appears to be a single-page application (SPA) that
loads map data dynamically after authentication.

To extract the zone data, you may need to:
1. Log in manually via browser
2. Open Developer Tools (F12) > Network tab
3. Look for GeoJSON or API calls when the Sales_Map loads
4. Copy the zone data URLs or raw GeoJSON

Alternatively, provide:
- Screenshot of the zones with visible boundaries
- Export feature if available in the portal
- Any downloadable shapefiles or KML files
    """)

    return None


def main():
    zones = extract_vipr_zones()

    if zones:
        print(f"\nSaving zones to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(zones, f, indent=2)
        print("Done!")
    else:
        print("\nCould not automatically extract zones.")
        print("Please provide the zone data manually or check browser Network tab.")


if __name__ == "__main__":
    main()
