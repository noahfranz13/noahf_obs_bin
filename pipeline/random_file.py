#!/usr/bin/env python
"""
A script to return a random h5 file at Berkeley.
"""
import bldw

assert __name__ == "__main__"

c = bldw.Connection()
meta = c.random_metadata_where("location LIKE %s", ("file://pd%",))
print(meta.filename())
