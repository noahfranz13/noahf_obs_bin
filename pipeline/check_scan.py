#!/usr/bin/env python
"""
A script to compare scan data between bltargets and bldw.
Usage: ./check_scan.py [ids]
"""
import bldw
import bltargets
import sys

def check(scan_id):
    print("analyzing data for scan", scan_id)
    blt = bltargets.Connection()
    scan = blt.fetch_scan(scan_id)
    print("found data from bltargets:", scan)
    dw = bldw.Connection()
    obs = dw.fetch_observation(scan_id)
    print("found data from bldw:", obs)
    if scan.timestamp() == obs.start_time:
        print("data matches")
    else:
        print("fixing bldw timestamp...")
        obs.start_time = scan.timestamp()
        dw.update_observation_start_time(obs)
        print("done")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        check(int(arg))
