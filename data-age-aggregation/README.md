# Age analyuer for OSM data

This tool uses a PBF-file (e.g. one of the files Geofabrik provides) and analyses the age of the data.

* Only timestamps are evaluated, no `check_date`-tags or similar.
* Only nodes and ways are evaluated. This makes it easier and the vast majority of objects are nodes and ways.

## Prerequisites

1. Download the PBF-file you want to analyse
2. Add location data via osmium, e.g. for the ` hamburg-latest` file with `osmium add-locations-to-ways hamburg-latest.osm.pbf -n --overwrite -o hamburg-latest-with-locations.osm.pbf`.
   * The `-n` is important as it keeps empty nodes within the file.

## Usage

Call the script with no args to see usage information: `Usage: go run . <pbf-path> <cell-size>`

Example: `go run . hamburg-latest.osm.pbf 0.002`

## Output data

The result is a GeoPackage file `output.geojson` containing cells (i.e. rectangles) with attributes regarding the age of the data within each polygon.
Use e.g. `ogr2ogr -f gpkg output.gpkg output.geojson` to convert it into a more convenient file format for further usage.

### Attributes:

The following attributes are set on the output features:

* `numberOfObjects`: Number of feature within the cell (nodes and ways).
* `ageMin`: Age in days of the youngest object (i.e. the most recent edited or created object)
* `ageAvg`: Average age in days of the objects.
* `ageMax`: Age in days of the oldest non-deleted object within this cell.