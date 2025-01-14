# Script for a OSM-GTFS-comparison

This is a simple comparison of **bus routes** from OSM and a GTFS dataset.
Currently it's not meant for any other public transport routes.

The output are some GeoJSON files describing routes only in OSM and routes missing in OSM.

## Usage

The following steps are needed:

1. Download the GTFS dataset
2. Convert the GTFS dataset into a GeoJSON file (see steps below)
3. Run the script: `./compare-osm-gtfs.py ./path/to/gtfs.geojson`

## GTFS to GeoJSON

https://github.com/blinktaginc/gtfs-to-geojson

`npm install gtfs-to-geojson -g`

### Usage

1. Download data and replace `.ZIP` by `.zip` is needed
2. Create `config.json` if not already exists (s. below)
3. `gtfs-to-geojson`

Result is for example in `./geojson/hvv/hvv.geojson` when your agency is "hvv".

### Config

This is for the HVV dataset (s. below):

```
{
  "agencies": [
    {
      "agency_key": "hvv",
      "path": "./Upload__hvv_Rohdaten_GTFS_Fpl_20241209.zip"
    }
  ],
  "bufferSizeMeters": 800,
  "coordinatePrecision": 5,
  "outputFormat": "lines-and-stops",
  "zipOutput": false
}
```

## HVV data

The HVV is the network around Hamburg, Germany.
The GTFS data for 2025 (as of 2024-12-09) is available here: https://daten.transparenz.hamburg.de/Dataport.HmbTG.ZS.Webservice.GetRessource100/GetRessource100.svc/82d4e6d2-ce59-4452-b1f2-64c6c329ffe4/Upload__hvv_Rohdaten_GTFS_Fpl_20241209.ZIP