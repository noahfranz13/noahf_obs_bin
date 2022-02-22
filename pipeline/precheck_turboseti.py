#!/usr/bin/env python
"""
This script errors if turboseti would be unable to handle a file.
Usage: ./precheck_turboseti.py <filename>
"""

from h5 import h5py
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: ./precheck_turboseti.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]

    h5file = h5py.File(filename, mode="r")
    data = h5file["data"]
    if data.shape[0] < 4 or data.shape == (1023, 1, 512):
        raise RuntimeError(f"turboseti cannot handle data with shape: {data.shape}")

