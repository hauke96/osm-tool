# Tagging saturation prediction

A tool to predict the amount of objects with a certain tag based on the current growth in tags.
Usually this growth is based on some logistic growth rate, meaning it eventually reaches a maximum value.
This is not entirely accurate for the real world, but this script tries to estimate this maximum value.

## Usage

Preparation:

* `python -m venv venv`
* `source venv/bin/activate`
* `pip3 install numpy matplotlib`

Usage:

* `./main.py`