#!/usr/bin/env python
"""
A script to check that the two different ways of guessing the observation for an h5 file match each other.
Usage: ./check_guess.py <h5file>
"""
import sys

import bldw
import bltargets
from h5 import h5py

assert __name__ == "__main__"

filename = sys.argv[1]

assert h5py.is_hdf5(filename)
h5file = h5py.File(filename, "r")

dw = bldw.Connection()
blt = bltargets.Connection()

try:
    scan_id = blt.guess_scan(h5file).id
except:
    scan_id = None
print("blt scan id:", scan_id)

try:
    obs_id = dw.guess_observation(h5file).id
except:
    obs_id = None
print("bldw obs id:", obs_id)

if scan_id != obs_id:
    print("************************************* mismatch *************************************")
