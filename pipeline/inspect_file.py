#!/usr/bin/env python
"""
A script to display information about an h5 file, like where else it exists.
"""

from astropy.time import Time
import os
import sys

import bldw
import bltargets
from h5 import h5py

assert __name__ == "__main__"

filename = sys.argv[1]
filename = os.path.normpath(filename)

print(sys.argv[0], filename)

h5file = h5py.File(filename, "r")
data = h5file["data"]
print("information from the file:")
print("data shape:", data.shape)
print(dict(data.attrs))
print("fch1:", data.attrs["fch1"])
print("foff:", data.attrs["foff"])
print("tsamp:", data.attrs["tsamp"])
print()

print("information from bldw:")
dw = bldw.Connection()
try:
    meta = dw.fetch_metadata_by_filename(filename)
except LookupError:
    print("bldw has no entry for this file")
    sys.exit(0)

print("observation id:", meta.observation_id)
print("tstart:", meta.tstart)
print("unix time:", meta.timestamp())
print("strtime:", meta.strtime())
print("frequency range:", meta.freq_low, "to", meta.freq_high)

print()
print("scan information from bltargets:")
blt = bltargets.Connection()
try:
    scan = blt.guess_scan(h5file)
    print(scan)
except LookupError as e:
    print("scan-guessing failed.")
    timestamp = bltargets.timestamp_from_h5(h5file)
    print("scans before timestamp:")
    for scan in blt.scans_before(timestamp, 3):
        print(scan)
    print("scans after timestamp:")
    for scan in blt.scans_after(timestamp, 3):
        print(scan)
    sys.exit(0)

if meta.observation_id != scan.id:
    print("warning: guess_scan data is inconsistent with the bldw database!")

try:
    obs = dw.fetch_observation(scan.id)
    print("bldw has matching observation data:")
    print(obs)
    print("receiver:", dw.fetch_receiver(obs.receiver_id).name)
except LookupError:
    print("there is no corresponding scan in bldw")

