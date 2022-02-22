#!/usr/bin/env python
"""
A script to untrack a data file from the database.
This is useful if we screwed up somewhere and tracked something that we don't want to track.

Usage: ./untrack.py [list of h5 files]
"""
import os
import sys

import bldw

def untrack(dw, filename):
    filename = os.path.normpath(filename)

    try:
        meta = dw.fetch_metadata_by_filename(filename)
    except LookupError:
        print(f"{filename} already isn't tracked.")
        return False

    dw.really_delete_meta(meta)
    print(f"{filename} untracked")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: untrack.py <filenames>")
        sys.exit(1)

    dw = bldw.retry_connection()
    for arg in sys.argv[1:]:
        untrack(dw, arg)
        
