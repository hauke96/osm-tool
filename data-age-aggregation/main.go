package main

import (
	"bufio"
	"context"
	"fmt"
	"github.com/hauke96/sigolo/v2"
	"github.com/paulmach/orb"
	"github.com/paulmach/osm"
	"github.com/paulmach/osm/osmpbf"
	"github.com/pkg/errors"
	"math"
	"os"
	"strconv"
	"strings"
	"time"
)

var cellSize = 1.0

type Cell struct {
	x               int
	y               int
	numberOfObjects int
	ageMin          int
	ageMax          int
	ageAvg          float64
}

func (c *Cell) add(ageInDays int) {
	c.ageMin = min(c.ageMin, ageInDays)
	c.ageMax = max(c.ageMax, ageInDays)
	c.ageAvg = (c.ageAvg*float64(c.numberOfObjects) + float64(ageInDays)) / float64(c.numberOfObjects+1)
	c.numberOfObjects += 1
}

func (c *Cell) asPolygon() orb.Polygon {
	minX := float64(c.x) * cellSize
	minY := float64(c.y) * cellSize
	maxX := minX + cellSize
	maxY := minY + cellSize
	return orb.Polygon{
		orb.Ring{
			orb.Point{minX, minY},
			orb.Point{minX, maxY},
			orb.Point{maxX, maxY},
			orb.Point{maxX, minY},
			orb.Point{minX, minY},
		},
	}
}

type CellIndex int64

func NewCellIndex(x int, y int) CellIndex {
	return CellIndex(int64(x)<<32 | int64(y))
}

func main() {
	if len(os.Args) != 3 || len(os.Args) >= 2 && (os.Args[1] == "-h" || os.Args[1] == "--help") {
		fmt.Printf(`Usage: go run . <pbf-path> <cell-size>

Parameters:
  pbf-path: Path within the Geofabrik-URL to download a file. The URL is constructed as follows: https://download.geofabrik.de/{pbf-path}-latest.osm.pbf
  cell-size: Size of the output cells in degree (e.g. a value of '1' means one latitude degree in width and 1 longitude degree in height)

Example: go run . hamburg-latest.osm.pbf 0.002
This uses the URL https://download.geofabrik.de/europe/germany/hamburg-latest.osm.pbf
`)
		os.Exit(0)
	}

	var err error

	filename := os.Args[1]
	reader, err := os.OpenFile(filename, os.O_RDONLY, 0644)
	if err != nil {
		sigolo.FatalCheck(errors.Wrapf(err, "Unable to open OSM input file file %s", filename))
	}

	cellSize, err = strconv.ParseFloat(os.Args[2], 64)
	sigolo.FatalCheck(errors.Wrapf(err, "Second parameter must be a floating-point number"))

	sigolo.Debug("Start reading OSM data")
	cells := map[CellIndex]*Cell{}
	processedNodes := 0
	processedWays := 0
	now := time.Now()
	scanner := osmpbf.New(context.Background(), reader, 1)
	for scanner.Scan() {
		switch obj := scanner.Object().(type) {
		case *osm.Node:
			if processedNodes == 0 {
				sigolo.Infof("Start processing nodes")
			}

			x := int(obj.Lon / cellSize)
			y := int(obj.Lat / cellSize)
			timestamp := obj.Timestamp

			processObject(x, y, cells, now, timestamp)

			processedNodes++
			if processedNodes%100000 == 0 {
				sigolo.Infof("Processed %d nodes", processedNodes)
			}
		case *osm.Way:
			if processedWays == 0 {
				sigolo.Infof("Start processing ways")
			}

			for _, node := range obj.Nodes {
				x := int(node.Lon / cellSize)
				y := int(node.Lat / cellSize)
				timestamp := obj.Timestamp
				processObject(x, y, cells, now, timestamp)
			}

			processedWays++
			if processedWays%100000 == 0 {
				sigolo.Infof("Processed %d ways", processedWays)
			}
		case *osm.Relation:
			// Skip relations since they do not contain the location data and only a few objects are relations (usually
			// way below 1%). The result will probably not much different if we include relations. However, this might
			// be added in a future version.
			sigolo.Infof("Reached relations in file. Skip them and end processing.")
			err = scanner.Close()
			sigolo.FatalCheck(err)
		}
	}
	endTime := time.Now()
	totalObjects := processedNodes + processedWays
	duration := endTime.Sub(now)
	sigolo.Infof("End processing %d OSM objects after %v (%v / 100k objects)", totalObjects, duration, time.Duration(duration.Nanoseconds()/100_000))

	storeToGeoJsonFile(cells)

	sigolo.Info("Done")
}

func processObject(x int, y int, cells map[CellIndex]*Cell, now time.Time, timestamp time.Time) {
	cellIndex := NewCellIndex(x, y)

	// Add cell is not exists
	if _, ok := cells[cellIndex]; !ok {
		cells[cellIndex] = &Cell{
			x:               x,
			y:               y,
			numberOfObjects: 0,
			ageMin:          999999, // >2700 years
			ageMax:          0,
			ageAvg:          0.0,
		}
	}

	cells[cellIndex].add(int(now.Sub(timestamp).Hours() / 24))
}

func storeToGeoJsonFile(cells map[CellIndex]*Cell) {
	featureTemplate := `{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f]]]},"properties":{"numberOfObjects":%d,"ageMin":%d,"ageMax":%d,"ageAvg":%d}},` + "\n"

	file, err := os.OpenFile("output.geojson", os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	sigolo.FatalCheck(err)
	defer file.Close()
	writer := bufio.NewWriter(file)

	_, err = writer.WriteString(`{"type": "FeatureCollection","features": [` + "\n")
	sigolo.FatalCheck(err)

	i := 0
	for _, cell := range cells {
		minX := float64(cell.x) * cellSize
		minY := float64(cell.y) * cellSize
		maxX := minX + cellSize
		maxY := minY + cellSize

		featureString := fmt.Sprintf(featureTemplate,
			minX, minY,
			minX, maxY,
			maxX, maxY,
			maxX, minY,
			minX, minY,
			cell.numberOfObjects,
			cell.ageMin,
			cell.ageMax,
			int(math.Round(cell.ageAvg)),
		)

		if i == len(cells)-1 {
			featureString = strings.TrimSuffix(featureString, ",\n") + "\n"
		}

		_, err = writer.WriteString(featureString)
		sigolo.FatalCheck(err)

		i++
	}

	_, err = writer.WriteString("]}")
	sigolo.FatalCheck(err)

	err = writer.Flush()
	sigolo.FatalCheck(err)
}
