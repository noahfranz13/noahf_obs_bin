#!/usr/bin/env python
"""
A tool to validate a text file full of target names.
"""

import bldw
import sys

assert __name__ == "__main__"

filename = sys.argv[1]
assert filename.endswith("txt")

print("checking for unknown targets...", file=sys.stderr)
dw = bldw.Connection()
found = 0
total = 0
for line in open(filename):
    target_name = line.strip()
    total += 1
    targets = dw.fetch_targets_by_name(target_name)
    if targets:
        if len(targets) > 1:
            print("warning: multiple targets are named", target_name, file=sys.stderr)
        found += 1
        continue
    print(target_name)
print(f"bldw entries found for {found}/{total} targets", file=sys.stderr)
