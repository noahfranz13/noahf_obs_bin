#!/usr/bin/env python
"""
A script to list all high-resolution h5 files, or at least the ones of a certain shape.
"""
import bldw

assert __name__ == "__main__"

c = bldw.Connection()

# Dimensions we are looking for
height = 16
width = 67108864

for meta in c.iter_metadata_where("location LIKE %s AND nsamples = %s AND nchans = %s", ("file://pd%", height, width)):
    print(meta.filename())
