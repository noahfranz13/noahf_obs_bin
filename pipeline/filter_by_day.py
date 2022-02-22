#!/usr/bin/env python
"""
Filters a list of filenames by what day they appear to be from.
Usage: ./filter_by_day.py <list of days> <list of filenames>
"""

import sys

day_file = sys.argv[1]
filenames_file = sys.argv[2]

days = set()
for line in open(day_file):
    day_string = line.strip()
    days.add(int(day_string))
print("loaded", len(days), "days", file=sys.stderr, flush=True)
    
for line in open(filenames_file):
    filename = line.strip()
    if "PKS" in filename:
        continue
    basename = filename.split("/")[-1]
    if "guppi_" not in basename:
        continue
    post_guppi = basename.split("guppi_")[-1]
    post_guppi_parts = post_guppi.split("_")
    post_guppi_int_parts = []
    for part in post_guppi_parts:
        try:
            post_guppi_int_parts.append(int(part))
        except ValueError:
            break
    if len(post_guppi_int_parts) != 2:
        continue
    day = post_guppi_int_parts[0]
    if day in days:
        print(filename)
