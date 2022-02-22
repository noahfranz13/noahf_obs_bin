#!/usr/bin/env python
"""
Prints out a list of directories that we suspect of being "stuck", where it looks like they have been transferred some time ago,
but the files still exist locally.

Run this on a machine like bls0 that has the bls directories mounted.

So what to do when you find stuck files?

Sometimes there is a copy of the stuck file already in gluster, but the track failed. Just rerun track.py on that file.

Sometimes the whole directory got deleted before it could be archived, perhaps for space reasons.
In this case, delete the transfer.done file in the directory to re-copy any h5s in the directory to Berkeley.

Sometimes two directories were named the same thing and the directories collided.
In this case, you'll have to resolve manually. You can try untracking and renaming one or both of the directories.

Sometimes something weirder is going on, like in the past I manipulated the .done files to pause processing, and subsequently
forgot what I was doing.
"""

import os
import sys
import time

import bldw
import machines


assert __name__ == "__main__"

dw = bldw.retry_connection()

checked_dirs = set()

ONE_DAY = 60 * 60 * 24

for meta in dw.iter_metadata_where("location LIKE %s AND deleted = %s", ("file://gb%", False)):
    # Process each directory once
    directory, _ = meta.filename().rsplit("/", 1)
    if directory in checked_dirs:
        continue
    checked_dirs.add(directory)

    assert os.path.isdir(directory)
    transfer_done = f"{directory}/transfer.done"
    if not os.path.exists(transfer_done):
        continue
    
    age = time.time() - os.path.getmtime(transfer_done)
    if age > 7 * ONE_DAY:
        print(directory)
