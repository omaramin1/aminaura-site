#!/usr/bin/env python3
"""
Convert Arcadia CSV to pins.geojson for the rep app.

This script takes the Arcadia export and creates a GeoJSON file with pins.
Since we don't have a geocoding API, it uses city center coordinates as approximations.

Usage:
    python convert_arcadia_to_pins.py arcadia_12_21.csv pins.geojson
"""

import csv
import json
import sys
import re
from collections import defaultdict

# City center coordinates for Virginia cities
CITY_COORDS = {
    'richmond': (-77.4360, 37.5407),
    'petersburg': (-77.4019, 37.2279),
    'fredericksburg': (-77.4605, 38.3032),
    'suffolk': (-76.5836, 36.7282),
    'norfolk': (-76.2859, 36.8508),
    'newport news': (-76.4730, 37.0871),
    'hampton': (-76.3452, 37.0299),
    'virginia beach': (-75.9780, 36.8529),
    'chesapeake': (-76.2875, 36.7682),
    'portsmouth': (-76.2983, 36.8354),
    'charlottesville': (-78.4767, 38.0293),
    'lynchburg': (-79.1422, 37.4138),
    'roanoke': (-79.9414, 37.2710),
    'danville': (-79.3950, 36.5860),
    'glen allen': (-77.5064, 37.6660),
    'chesterfield': (-77.5061, 37.3774),
    'henrico': (-77.4200, 37.5500),
    'mechanicsville': (-77.3730, 37.6090),
    'colonial heights': (-77.4103, 37.2440),
    'hopewell': (-77.2872, 37.3043),
    'default': (-77.4360, 37.5407)  # Richmond as default
}

def extract_city(address):
    """Extract city from address string."""
    if not address:
        return 'default'

    # Address format: "123 Street, City, VA, 12345"
    parts = address.split(',')
    if len(parts) >= 2:
        city = parts[-3].strip().lower() if len(parts) >= 3 else parts[-2].strip().lower()
        # Clean up city name
        city = re.sub(r'\d+', '', city).strip()
        return city
    return 'default'

def get_coords_for_city(city):
    """Get coordinates for a city, with slight randomization."""
    import random
    city_lower = city.lower().strip()

    # Try exact match
    if city_lower in CITY_COORDS:
        base = CITY_COORDS[city_lower]
    else:
        # Try partial match
        for key in CITY_COORDS:
            if key in city_lower or city_lower in key:
                base = CITY_COORDS[key]
                break
        else:
            base = CITY_COORDS['default']

    # Add slight randomization so pins don't stack exactly
    lng = base[0] + (random.random() - 0.5) * 0.02
    lat = base[1] + (random.random() - 0.5) * 0.02
    return (lng, lat)

def determine_pin_type(row):
    """Determine pin type based on row data."""
    tpv_status = row.get('TPV Status', '').lower()
    order_status = row.get('Order Status', '').lower()

    if 'complete' in tpv_status:
        return 'complete'
    elif 'not complete' in tpv_status or 'pending' in tpv_status:
        return 'pending'
    elif 'cancel' in order_status or 'reject' in order_status:
        return 'invalid'
    else:
        return 'pending'

def convert_csv_to_geojson(input_file, output_file):
    """Convert Arcadia CSV to pins GeoJSON."""
    features = []
    stats = defaultdict(int)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            address = row.get('Customer Address', '')
            if not address:
                continue

            city = extract_city(address)
            coords = get_coords_for_city(city)
            pin_type = determine_pin_type(row)

            feature = {
                "type": "Feature",
                "properties": {
                    "type": pin_type,
                    "status": row.get('TPV Status', ''),
                    "order_status": row.get('Order Status', ''),
                    "rep": row.get('Rep Name', ''),
                    "date": row.get('Sale Date', ''),
                    "city": city,
                    "dwelling": row.get('Dwelling Type', ''),
                    "lmi_type": row.get('LMI Qualification Type', '')
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": list(coords)
                }
            }

            features.append(feature)
            stats[pin_type] += 1
            stats['total'] += 1

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_file, 'w') as f:
        json.dump(geojson, f)

    print(f"Converted {stats['total']} pins:")
    print(f"  - Complete (valid): {stats['complete']}")
    print(f"  - Pending: {stats['pending']}")
    print(f"  - Invalid: {stats['invalid']}")
    print(f"Saved to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert_arcadia_to_pins.py input.csv output.geojson")
        sys.exit(1)

    convert_csv_to_geojson(sys.argv[1], sys.argv[2])
