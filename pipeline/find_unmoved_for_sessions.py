#!/usr/bin/env python
"""
Find unmoved directories for a provided text file full of sessions.
"""

import argparse
import sys

import pipeline

assert __name__ == "__main__"

parser = argparse.ArgumentParser(description="find unmoved directories")
parser.add_argument("sessionlist")
parser.add_argument("--start", help="session to start at")
args = parser.parse_args()

found_start = False
for line in open(args.sessionlist):
    session = line.strip()
    if "#" in session:
        continue
    if session == args.start:
        found_start = True
    if not found_start and args.start:
        continue
    print("processing", session, file=sys.stderr, flush=True)
    unmoved = pipeline.find_unmoved(session, "bls0", "/mnt_blc*/datax*")
    for d in unmoved:
        print(f"/mnt_{source.host}{d}", flush=True)
