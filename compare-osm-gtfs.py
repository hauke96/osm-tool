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

# Query for whole Germany (relation 3600062782):
queryUrlString = urllib.parse.quote("""
[out:json][timeout:60];
area(id:3600062782)->.searchArea;
(
  relation["route"="bus"]["network:short"="HVV"](area.searchArea);
);
convert item ::=::,::geom=geom(),_osm_type=type();
out geom;
""")
url = f"https://overpass-api.de/api/interpreter?data={queryUrlString}"

osmBusRoutesJsonFileObject = Path(osmBusRoutesJsonFile)
try:
    osmBusRoutesJsonFileObject.resolve(strict=True)
except FileNotFoundError:
    print(f"Download raw OSM data to {osmBusRoutesJsonFile}")
    response = requests.get(url)
    osmJsonString = response.text
    with open(osmBusRoutesJsonFile, "w") as f:
        f.write(osmJsonString)
else:
    print(f"File {osmBusRoutesJsonFile} already exists and will be used")
    with open(osmBusRoutesJsonFile, 'r') as f:
        osmJsonString = f.read().replace('\n', '')

#
# 2. Create GeoJSON and write to file
#

osmRouteNumbers = set()

print("Create GeoJSON")
osmJson = json.loads(osmJsonString)
geojsonObjects = []
for element in osmJson["elements"]:
    ref = element["tags"].get("ref", "").lower()
    name = element["tags"].get("name", "").lower()
    if ref.startswith("n") or \
        "sev" in ref or \
        "flixbus" in name or \
        not "geometry" in element:
        continue

    geojsonObject = geojson.Feature(
        geometry = element["geometry"],
        properties = element["tags"]
    )

    osmRouteNumbers.add(ref)

    geojsonObjects.append(geojsonObject)

print(f"Write GeoJSON to {osmBusRoutesGeojsonFile}")
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

    # route_type 3 means "bus routes"
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
    routeNumber = element.properties.get("route_short_name", None)

    # route_type 3 means "bus routes"
    #if element["geometry"]["type"] != "LineString" or element.properties["route_type"] != "3" or routeNumber == None or "sev" in routeNumber.lower():
    #    continue

    if routeNumber != None and routeNumber.lower() in routesOnlyInGtfs:
        elementsToStore.append(element)

print(f"Write routes missing in OSM to GeoJSON file {osmMissingBusRoutesGeojsonFile}")
featureCollection = geojson.FeatureCollection(elementsToStore)
with open(osmMissingBusRoutesGeojsonFile, "w") as f:
    geojson.dump(featureCollection, f, indent=4, sort_keys=True)