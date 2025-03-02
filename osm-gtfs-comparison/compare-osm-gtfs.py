#!/usr/bin/env python

# Usage: ./load-osm-bus.routes.py ./path/to/gtfs.geojson

from pathlib import Path
import urllib.parse
import requests
import json
import geojson
import sys

osmBusRoutesJsonFile = "bus-routes-in-osm.json"
osmBusRoutesGeojsonFile = "bus-routes-in-osm.geojson"
osmOnlyBusRoutesGeojsonFile = "bus-routes-only-in-osm.geojson"
osmMissingBusRoutesGeojsonFile = "bus-routes-missing-in-osm.geojson"

#
# 1. Load OSM data
#

# Area IDs:
#  Germany: 3600051477
#  HVV    : 3604189510
# Add  ["network:short"="HVV"]  if you want to filter not by HVV-area but by tag.
queryUrlString = urllib.parse.quote("""
[out:json][timeout:60];
area(id:3604189510)->.searchArea;
(
  relation["route"="bus"](area.searchArea);
);
convert item ::=::,::geom=geom(),_osm_type=type();
out geom;
""")
url = f"https://overpass-api.de/api/interpreter?data={queryUrlString}"

osmBusRoutesJsonFileObject = Path(osmBusRoutesJsonFile)
try:
    osmBusRoutesJsonFileObject.resolve(strict=True)
except FileNotFoundError:
    # No local file -> Execute query and store the result
    print(f"Download raw OSM data to {osmBusRoutesJsonFile}")
    response = requests.get(url)
    osmJsonString = response.text
    with open(osmBusRoutesJsonFile, "w") as f:
        f.write(osmJsonString)
else:
    # JSON file already exists from prior query execution -> use the existing file
    print(f"File {osmBusRoutesJsonFile} already exists and will be used")
    with open(osmBusRoutesJsonFile, 'r') as f:
        osmJsonString = f.read().replace('\n', '')

#
# 2. Create GeoJSON and write to file
#

osmRouteNumbers = set()

print("Create GeoJSON of OSM data")
osmJson = json.loads(osmJsonString)
geojsonObjects = []
for element in osmJson["elements"]:
    ref = element["tags"].get("ref", "").lower()
    name = element["tags"].get("name", "").lower()

    # Ignore certain bus routes like long-distant busses (in Germany mainly FlixBus) or rail-replacement-services (SEV)
    if ref.startswith("n") or \
        "sev" in ref or \
        "flixbus" in name or \
        not "geometry" in element:
        continue

    geometry = element["geometry"]

    # Unwrap OSM LineStrings, which consist of Point and LineString geometries. We only want the routes, so only the lines themselves.
    if geometry["type"] == "GeometryCollection":
        newGeometries = []
        for childGeometry in geometry["geometries"]:
            if childGeometry["type"] == "LineString":
                newGeometries.append(childGeometry["coordinates"])
        geometry = geojson.MultiLineString(newGeometries)

    osmRouteNumbers.add(ref)

    geojsonObject = geojson.Feature(
        geometry = geometry,
        properties = element["tags"]
    )
    geojsonObjects.append(geojsonObject)

print(f"Write GeoJSON of OSM data to {osmBusRoutesGeojsonFile}")
geojsonFeatureCollection = geojson.FeatureCollection(geojsonObjects)
with open(osmBusRoutesGeojsonFile, "w") as f:
    geojson.dump(geojsonFeatureCollection, f, indent=4, sort_keys=True)

#
# 3. Load GTFS GeoJSON
#

print("Load GTFS GeoJSON data")

gtfsRouteNumbers = set()

gtfsGeojsonFile = sys.argv[1]
with open(gtfsGeojsonFile, 'r') as f:
    gtfsGeojson = geojson.loads(f.read())

for element in gtfsGeojson["features"]:
    routeNumber = element.properties.get("route_short_name", "").lower()
    routeType = str(element.properties.get("route_type", -1)).lower()

    # Only consider LineStrings and bus routes (route_type 3)(
    if "LineString" not in element["geometry"]["type"] or \
        routeType != "3" or \
        "sev" in routeNumber.lower():
        continue

    gtfsRouteNumbers.add(routeNumber)

#
# 4. Calculate difference in route numbers
#

print("Analyze OSM and GTFS routes")

routesOnlyInOsm = osmRouteNumbers - gtfsRouteNumbers
routesOnlyInGtfs = gtfsRouteNumbers - osmRouteNumbers

print(f"Routes in OSM:\n{osmRouteNumbers}")
print()
print(f"Routes in GTFS:\n{gtfsRouteNumbers}")
print()
print(f"Routes in OSM but not in GTFS:\n{routesOnlyInOsm}")
print()
print(f"Routes in GTFS but not in OSM:\n{routesOnlyInGtfs}")

#
# 5. Create separate GeoJSON files for routes
#

# 5.1 Routes only in OSM
print("Filter routes only in OSM")
with open(osmBusRoutesGeojsonFile, 'r') as f:
    osmGeojson = geojson.loads(f.read())

elementsToStore = []
for element in osmGeojson["features"]:
    if element.properties["ref"] in routesOnlyInOsm:
        elementsToStore.append(element)

print(f"Write routes only in OSM to GeoJSON file {osmOnlyBusRoutesGeojsonFile}")
featureCollection = geojson.FeatureCollection(elementsToStore)
with open(osmOnlyBusRoutesGeojsonFile, "w") as f:
    geojson.dump(featureCollection, f, indent=4, sort_keys=True)

# 5.2 Routes missingin OSM
print("Filter routes missing in OSM")
with open(gtfsGeojsonFile, 'r') as f:
    gtfsGeojson = geojson.loads(f.read())

elementsToStore = []
for element in gtfsGeojson["features"]:
    routeNumber = element.properties.get("route_short_name", "")
    if routeNumber.lower() in routesOnlyInGtfs:
        elementsToStore.append(element)

print(f"Write routes missing in OSM to GeoJSON file {osmMissingBusRoutesGeojsonFile}")
featureCollection = geojson.FeatureCollection(elementsToStore)
with open(osmMissingBusRoutesGeojsonFile, "w") as f:
    geojson.dump(featureCollection, f, indent=4, sort_keys=True)