# Age analyuer for OSM data

This tool downloads a PBF-file from Geofabrik and analyses the age of the data.

* Only timestamps are evaluated, no `check_date`-tags or similar.
* Only nodes and ways are evaluated. This makes it easier and the vast majority of objects are nodes and ways.

## Usage

Call the script with no args to see usage information: `python3 ./script.py`

Example: `python3 ./script.py "europe/germany/hamburg" 0.002`

### Caching

In case a `data.osm.pbf` file is present, this file will be used.
Delete this file to force a fresh download of the PBF file.

## Output data

The result is a GeoPackage file `output.gpkg` containing cells (i.e. rectangles) with attributes regarding the age of the data within each polygon.

### Attributes:

The following attributes are set on the output features:

* `numberOfObjects`: Number of feature within the cell (nodes and ways).
* `ageMin`: Age in days of the youngest object (i.e. the most recent edited or created object)
* `ageAvg`: Average age in days of the objects.
* `ageMax`: Age in days of the oldest non-deleted object within this cell.