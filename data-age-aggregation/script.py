#!/usr/bin/env python3

import urllib.request
import sys
import os.path
import osmium
from datetime import datetime
import locale
import geopandas as gpd
from shapely.geometry import Polygon
import time

# For number formatting:
locale.setlocale(locale.LC_ALL, '')

osmPbfFile = "./data.osm.pbf"
outputFile = "output.gpkg"
now = datetime.now()

if len(sys.argv) == 1:
    print("Usage: python3 %s <pbf-path> <cell-size-in-deg>" % sys.argv[0])
    print()
    print("Parameters:")
    print("  pbf-path: Path within the Geofabrik-URL to download a file. The URL is constructed as follows: https://download.geofabrik.de/{pbf-path}-latest.osm.pbf")
    print("  cell-size-in-deg: Size of the output cells in degree (e.g. a value of '1' means one latitude degree in width and 1 longitude degree in height)")
    print()
    print("Example: python3 %s europe/germany/hamburg 0.002" % sys.argv[0])
    print("This uses the URL https://download.geofabrik.de/europe/germany/hamburg-latest.osm.pbf")
    sys.exit(-1)

# e.g. "europe/germany/hamburg" for https://download.geofabrik.de/europe/germany/hamburg-latest.osm.pbf
osmPbfUrlPath = sys.argv[1]
cellSize = float(sys.argv[2])

url = f"https://download.geofabrik.de/{osmPbfUrlPath}-latest.osm.pbf"

if not os.path.isfile(osmPbfFile):
    print(f"Download OSM-PBF from {url} to {osmPbfFile}")
    urllib.request.urlretrieve(url, osmPbfFile)
    print("Download of OSM-PBF file complete")
else:
    print(f"Do NOT download PBF file, since OSM file {osmPbfFile} already exists. I'll use that.")

class Cell:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.numberOfObjects = 0
        self.ageMin = 999999 # >2700 years
        self.ageMax = 0
        self.ageAvg = 0

    def add(self, ageInDays):
        self.ageMin = min(self.ageMin, ageInDays)
        self.ageMax = max(self.ageMax, ageInDays)
        self.ageAvg = (self.ageAvg * self.numberOfObjects + ageInDays) / (self.numberOfObjects + 1)
        self.numberOfObjects += 1

    def asPolygon(self):
        minX = self.x * cellSize
        minY = self.y * cellSize
        maxX = minX + cellSize
        maxY = minY + cellSize
        return Polygon([
                [minX, minY],
                [minX, maxY],
                [maxX, maxY],
                [maxX, minY],
                [minX, minY]
            ])

    def __str__(self):
        return f"Cell(xy=[{self.x},{self.y}], numberOfObjects={self.numberOfObjects}, ageMin={self.ageMin}, ageMax={self.ageMax}, ageAvg={self.ageAvg})"

print("Start processing OSM objects")
cells = {}
processedNodes = 0
processedWays = 0
start = time.time()
for obj in osmium.FileProcessor(osmPbfFile).with_locations():
    match obj.type_str():
        case "n":
            if processedNodes == 0:
                print("Start processing nodes")

            cellIndex = (int(obj.lon / cellSize), int(obj.lat / cellSize))

            # Add cell is not exists
            if cellIndex not in cells:
                cells[cellIndex] = Cell(cellIndex[0], cellIndex[1])

            cells[cellIndex].add((now-obj.timestamp.replace(tzinfo=None)).days)

            processedNodes += 1
            if processedNodes % 100000 == 0:
                print(f"Processed {processedNodes:n} nodes")
        case "w":
            if processedWays == 0:
                print("Start processing ways")

            cellIndices = set()
            ageInDays = (now-obj.timestamp.replace(tzinfo=None)).days

            for node in obj.nodes:
                cellIndex = (int(node.lon / cellSize), int(node.lat / cellSize))
                cellIndices.add(cellIndex)

            for cellIndex in cellIndices:
                # Add cell is not exists
                if cellIndex not in cells:
                    cells[cellIndex] = Cell(cellIndex[0], cellIndex[1])

                cells[cellIndex].add(ageInDays)

            processedWays += 1
            if processedWays % 100000 == 0:
                print(f"Processed {processedWays:n} ways")
end = time.time()
totalNumberOfObjects = processedNodes + processedWays
durationInS = end - start
print(f"Done processing OSM objects within {durationInS:.2f}s ({(durationInS / totalNumberOfObjects)*100000:.2f}s per 100k)")
print(f"  Processed {processedNodes} nodes and {processedWays} ways ({totalNumberOfObjects} objects in total)")

print("Generate features for cells")
cellData = []
for c in cells:
    cell = cells[c]
    cellData.append({
        "geometry": cell.asPolygon(),
        "numberOfObjects": cell.numberOfObjects,
        "ageMin": cell.ageMin,
        "ageMax": cell.ageMax,
        "ageAvg": cell.ageAvg
    })

print(f"Write cell features to {outputFile}")
frame = gpd.GeoDataFrame(cellData, crs="EPSG:4326")
frame.to_file(filename=outputFile, driver="GPKG")

print("Done")