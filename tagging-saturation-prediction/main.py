#!/usr/bin/env python3

import csv
import sys
import numpy
import math
import matplotlib.pyplot as plt
import colorsys

def logisticFunc(L, k, x0, x):
    return L / (1 + math.exp(-1 * k * (x - x0)))

xValues = []
yValues = []

# L = Assumed saturation maximum
Lmin=0
Lmax=0

# k = Growth rate (steepness of curve)
kmin=0
kmax=0

# x0 = Mid-point of curve where the growth starts to slow down
x0min=0
x0max=0

accuracy=10

dataFileName="data.txt"
print(f"Read {dataFileName}")
with open(dataFileName) as dataFile:
    for lineIdx, line in enumerate(dataFile):
        if line.strip().startswith("#"):
            continue

        splitLine = line.split(",")
        if len(splitLine) != 2:
            print(f"Error at line {lineIdx+1}: Two comma separated values expected but found {len(splitLine)}.")
            sys.exit(1)
        elif splitLine[0] == "Lmin":
            Lmin = float(splitLine[1])
        elif splitLine[0] == "Lmax":
            Lmax = float(splitLine[1])
        elif splitLine[0] == "kmin":
            kmin = float(splitLine[1])
        elif splitLine[0] == "kmax":
            kmax = float(splitLine[1])
        elif splitLine[0] == "x0min":
            x0min = float(splitLine[1])
        elif splitLine[0] == "x0max":
            x0max = float(splitLine[1])
        elif splitLine[0] == "accuracy":
            accuracy = float(splitLine[1])
        else:
            try:
                xValues.append(float(splitLine[0]))
                yValues.append(float(splitLine[1]))
            except ValueError:
                print(f"Error at line {lineIdx+1}: Expected two float numbers but found x={splitLine[0]} and y={splitLine[1]}.")
                sys.exit(2)

print("Start searching for optimal value combination")

# Format: [L, l, x0, err_absolute]
results=[]

yValuesSum = sum(yValues)

for L in numpy.arange(Lmin, Lmax, (Lmax-Lmin)/accuracy):
    for k in numpy.arange(kmin, kmax, (kmax-kmin)/accuracy):
        for x0 in numpy.arange(x0min, x0max, (x0max-x0min)/accuracy):
            yValuesCalculated = []
            for x in xValues:
                # See https://en.wikipedia.org/wiki/Logistic_function
                yCalculated = logisticFunc(L, k, x0, x)
                yValuesCalculated.append(yCalculated)

            errAbsolute = sum([abs(a-b) for a, b in zip(yValuesCalculated, yValues)])
            results.append([L, k, x0, errAbsolute])

resultFileName = "result.csv"
print(f"Done, write result as CSV to {resultFileName}")
with open(resultFileName, 'w') as resultFile:
    resultFile.write("L,k,x0,err_absolute\n")
    for row in results:
        resultFile.write(','.join(map(str, row)) + '\n')

print("Some statistics:")

# Sort by absolute error
sortedByErrAbsolute = sorted(results, key = lambda r: r[3])

n = 10
print(f"  Best {n} result with lowest error values:")
for i in range(0, n):
    print(f"    {i}. L={sortedByErrAbsolute[i][0]}, k={sortedByErrAbsolute[i][1]}, x0={sortedByErrAbsolute[i][2]}, err_absolute={sortedByErrAbsolute[i][3]}")

n = int(accuracy)
print(f"  Average over {n} best values:")
Lavg = sum([a[0] for a in sortedByErrAbsolute[0:n]]) / n
kavg = sum([a[1] for a in sortedByErrAbsolute[0:n]]) / n
x0avg = sum([a[2] for a in sortedByErrAbsolute[0:n]]) / n
errAbsoluteAvg = sum([a[3] for a in sortedByErrAbsolute[0:n]]) / n
print(f"    L={Lavg}, k={kavg}, x0={x0avg}, err_absolute={errAbsoluteAvg}")

# 90% of saturation value
saturationFactor = 0.9
nearlySaturatedMaxValue = Lavg * saturationFactor
x = x0avg - (1 / kavg) * math.log((Lavg - nearlySaturatedMaxValue) / nearlySaturatedMaxValue)

print("  Based on the average result:")
print(f"    In {int(x)}, OSM will contain about {int(saturationFactor*100)}% of the real existing amount of data of the type you have analyzed here.")

# Create plots
n = int(accuracy)
samples = 100
xSteps = numpy.arange(x0avg-10, x0avg+20, 30/samples)
for i in range(0, n):
    L = sortedByErrAbsolute[i][0]
    k = sortedByErrAbsolute[i][1]
    x0 = sortedByErrAbsolute[i][2]
    y = [logisticFunc(L, k, x0, x) for x in xSteps]

    hsv = colorsys.rgb_to_hls(20/255, 100/255, 190/255)
    l = hsv[1] + ((1 - hsv[1]) * 0.8 * i / n)
    rgb = colorsys.hls_to_rgb(hsv[0], l, hsv[2])
    plt.plot(xSteps, y, color=rgb)

plt.savefig('result.png')