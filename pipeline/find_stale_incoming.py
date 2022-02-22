#!/usr/bin/env python
"""
Look for data that got transferred but cannot be picked up for the archive stage.
This is directories on the blpd machine used for "incoming" which have no zmanifest.csv (so they
cannot be archived) but also all of their files are more than some threshold of oldness.
"""

import machines
import os
import remote

assert __name__ == "__main__"
assert machines.in_berkeley()

host = "blpd18"

all_files = remote.retry_run_one(host, "find /datax/incoming/pipeline")
new_files = remote.retry_run_one(host, "find /datax/incoming/pipeline -mtime -7")

ok_dirs = set()
all_dirs = set()

for f in all_files:
    d = os.path.dirname(f)

    if f.endswith("h5"):
        all_dirs.add(d)
    
    if f.endswith("zmanifest.csv"):
        # This directory is ready to archive so it's fine
        ok_dirs.add(d)

for f in new_files:
    d = os.path.dirname(f)
    if f.endswith("h5"):
        # This directory has a new file so it's fine
        ok_dirs.add(d)

for d in sorted(all_dirs):
    if d in ok_dirs:
        continue
    print(d)
