#!/usr/bin/env python
"""
Usage: ./grep_files.py <pattern>
Prints out info for all files matching this pattern
"""

import sys

import bldw

assert __name__ == "__main__"

arg = sys.argv[1]
print(arg)
c = bldw.Connection()
pattern = "%" + arg + "%"
metas = c.fetch_metadata_where("location LIKE %s", (pattern,))
print(len(metas), "files match", arg)
for m in metas:
    print(m)
