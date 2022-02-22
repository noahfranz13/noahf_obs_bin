#!/usr/bin/env python
"""
Find out how much of what sort of stuff is on the bls disks.
"""

import machines
import remote
import sys

assert __name__ == "__main__"

filetypes = ["fil", "h5", "x2h"]
filetype_size = dict((ft, 0) for ft in filetypes)
disks = ["datax", "datax2", "datax3"]
mdf_size = {}
for m in machines.BLS_MACHINES:
    for d in disks:
        mdf_size[(m, d)] = dict((ft, 0) for ft in filetypes)

def nice_t(filesize):
    return f"{filesize/1_000_000_000:.2f}T"

for filetype in filetypes:
    for m in machines.BLS_MACHINES:
        for disk in disks:
            lines = remote.retry_run_one(m, f"find /{disk}/pipeline -name '*.{filetype}' -print0 | du -c --files0-from=- | tail -1 | cut -f1")
            size = float(lines[0])
            filetype_size[filetype] += size
            mdf_size[(m, disk)][filetype] += size
            print(m, disk, filetype, nice_t(size))

    print()
    print("* * * * * * * * * * * * * * * * * * * * * * * * *")
    print()
    print(nice_t(filetype_size[filetype]), f"total .{filetype}")
    print()
    print("* * * * * * * * * * * * * * * * * * * * * * * * *")
    print()

    if "--fil" in sys.argv:
        sys.exit(0)

found = False
for (m, disk), fmap in mdf_size.items():
    if fmap["x2h"] > 0 and fmap["h5"] == 0 and fmap["fil"] == 0:
        print(f"consider running on {m}:")
        print(f"find /{disk}/pipeline -name '*.x2h' -delete")
        print()
        found = True

if not found:
    print("no x2h cleanup candidates.")
    
