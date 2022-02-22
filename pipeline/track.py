#!/usr/bin/env python
"""
A script to track data files in bldw.

Usage: ./track.py <filename> [flags]

It checks if the file is tracked already, and if not, adds a Metadata database entry.

If the --copy flag is provided, it expects this to be a copy, and raises an error if we do
not already have this metadata stored elsewhere.

If the --dir flag is provided, it expects a directory, and tracks all .h5 files in the directory.
"""
from h5 import h5py

import datetime
import os
import sys

import bldw
import h5util

def log(message):
    print(f"[{datetime.datetime.now()}] {message}", flush=True)

    
def track(filename, dw=None):
    filename = os.path.normpath(filename)

    if dw is None:
        dw = bldw.retry_connection()
    try:
        meta = dw.fetch_metadata_by_filename(filename)
    except LookupError:
        log("bldw is not tracking this file yet.")
    else:
        if meta.deleted:
            raise RuntimeError("bldw says this file was deleted. this case is currently not handled")
        log("this file is already being tracked.")
        return

    # One of these operations should fail if the data has been corrupted. Better to catch it now.
    h5file = h5py.File(filename, "r")
    h5util.check_valid(h5file)

    # Find the observation that corresponds to this file, by checking timestamps.
    try:
        obs = dw.guess_observation(h5file)
    except LookupError as e:
        log("we cannot match this file to an observation. using null observation_id.")
        local_meta = bldw.Metadata.from_h5(h5file, None)
        dw.insert_meta(local_meta)
        log("inserted new metadata entry. tracking successful, sort of.")
        return
    log(f"found a matching observation: {obs}")

    local_meta = bldw.Metadata.from_h5(h5file, obs.id)

    # See if we already have this data somewhere else.
    metas = dw.fetch_metadata_by_observation_id(obs.id)
    for m in metas:
        if local_meta.same_data(m):
            adverb = "previously" if m.deleted else "currently"
            log(f"this appears to be a copy of the data {adverb} at {m.location}")
            break
    else:
        if "--copy" in sys.argv:
            raise RuntimeError("we expected this file to be a copy, but it is not")

    dw.insert_meta(local_meta)
    log("inserted new metadata entry. tracking successful")

    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        log("usage: track.py <filename> [flags]")
        sys.exit(1)
    flags = ["--copy", "--dir"]
    for arg in sys.argv[2:]:
        if arg not in flags:
            log("unrecognized arg:", arg)
            sys.exit(1)

    dw = bldw.retry_connection()
            
    filename = sys.argv[1]
    if "--dir" in sys.argv:
        basenames = [f for f in os.listdir(filename) if f.endswith(".h5")]
        for basename in sorted(basenames):
            fullname = os.path.join(filename, basename)
            log(f"tracking {fullname}")
            track(fullname, dw=dw)
    else:
        track(filename, dw=dw)
