#!/usr/bin/env python
"""
A script to check that an h5 file is readable.
Just throws an exception if it isn't.
Usage: ./check_h5.py <h5file>
"""
import sys

from h5 import h5py
import h5util

assert __name__ == "__main__"

filename = sys.argv[1]

assert h5py.is_hdf5(filename)
h5file = h5py.File(filename, "r")
h5util.check_valid(h5file)
