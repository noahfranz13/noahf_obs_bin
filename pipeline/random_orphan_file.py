#!/usr/bin/env python
"""
A script to return a random h5 file at Berkeley that has no associated observation.
"""
import bldw

assert __name__ == "__main__"

c = bldw.Connection()
meta = c.random_metadata_where("location LIKE %s AND observation_id IS NULL", ("file://pd%",))
print("filename:", meta.filename())
print("time:", meta.strtime())

