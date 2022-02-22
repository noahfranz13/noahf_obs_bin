#!/usr/bin/env python

from astropy.time import Time
import os
import sys

import bldw
import bltargets
from h5 import h5py


def lookup(filename):
    filename = os.path.normpath(filename)
    f = h5py.File(filename, "r")

    ### Check bltargets
    blt = bltargets.Connection()
    scan = None
    try:
        scan = blt.guess_scan(f)
    except LookupError as e:
        print(f"ERROR: {e}")
    else:
        print("this file matches a scan:")
        print(scan)

    ### Check bldw
    dw = bldw.Connection()
    meta = None
    try:
        meta = dw.fetch_metadata_by_filename(filename)
    except LookupError:
        print("this file is untracked in bldw.")
    else:
        print("this file is tracked in bldw:")
        print(meta)
        
    ### Compare to other information for this scan/observation
    local_meta = bldw.Metadata.from_h5(f, scan.id)
    metas = dw.fetch_metadata_by_observation_id(scan.id)
    if metas:
        s = "s" if len(metas) > 1 else ""
        print(f"we are tracking {len(metas)} other file{s} for this observation:")
        for meta in metas:
            print(meta)
    else:
        print("we are not tracking any other files for this observation")

    for m in metas:
        if local_meta.same_data(m):
            if m.deleted:
                print(f"this data was previously stored at {m.location}")
            else:
                print(f"this data is also stored at {m.location}")

        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            lookup(filename)
    else:
        print("usage: lookup.py <filename>")
