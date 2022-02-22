#!/usr/bin/env python
"""
Designed so that you can run
./safe_archive.py <list of h5 files or directories>
and it will check if it's safe to put into the archive.
"""
import glob
import grp
import os
import pwd
import shutil
import subprocess
import sys

import bldw
import btldata
from h5 import h5py
from track import track

DIRMAP = [
    ("/datag/blpd13/datax/holding_lband_jan2020", "/datag/blpd13/datax/dl"),
    ("/datag/blpd13/datax/holding_sband_jan2020", "/datag/blpd13/datax/dl"),
]


def fail(message):
    print("error:", message)
    sys.exit(1)

def safe_archive(input_filename):
    print(f"running safe_archive on {input_filename}")
    
    filename = os.path.realpath(input_filename)
    if input_filename != filename:
        print("real path for", input_filename, "is", filename)

    assert filename.endswith(".h5")
    if "pipeline" in filename:
        fail(f"{filename} already contains the word pipeline in it, so we think it's already archived")

    if "Parkes" in filename or "PKS" in filename:
        fail("this filename looks like Parkes data")

    h5file = h5py.File(filename, "r")
    attrs = h5file["data"].attrs
    telescope_id = attrs["telescope_id"].item()
    if telescope_id != 6:
        fail(f"telescope id is {telescope_id}")

    if filename.startswith("/mnt"):
        fail("this should be run locally, not on /mnt_x directories")

    # Figure out where we should look for other files hardlinked to this one
    base_dir = None
    for base1, base2 in DIRMAP:
        if filename.startswith(base1):
            base_dir = base2
            break

    # Look for hard links to this file
    num_hard_links = os.stat(filename).st_nlink

    if num_hard_links > 1:
        if base_dir is None:
            fail(f"we need alts but there is no hardcoded partner directory for {filename}")            
        alts = subprocess.check_output(["find", base_dir, "-samefile", filename]).decode("utf-8").strip().split()
        print("alternate hardlinks found:")
        for alt in alts:
            print(alt)
        if num_hard_links != len(alts) + 1:
            fail("we could not find all alts")
    else:
        print("no alts expected")
        alts = []


    # Check that all the permissions are correct
    for f in [filename] + alts:
        stat = os.stat(f)
        user_owner = pwd.getpwuid(stat.st_uid).pw_name
        if user_owner != "obs":
            fail(f"file {f} is owned by user {user_owner}, not obs. try sudo chown obs:obs <file>")
        group_owner = grp.getgrgid(stat.st_gid).gr_name
        if group_owner != "obs":
            fail(f"file {f} is owned by group {group_owner}, not obs. try sudo chown obs:obs <file>")
        d = os.path.dirname(f)
        if not os.access(d, os.W_OK):
            fail(f"we do not have write permission to the directory {d}. try sudo chown obs:obs <dir>")

    # Figure out what the ideal target basename is
    basename_candidates = [os.path.basename(f) for f in [filename] + alts if "guppi" in f]
    if len(basename_candidates) != 1:
        fail("we could not determine the ideal basename")
    basename = basename_candidates[0]
    print("ideal basename:", basename)

    # Match our filenames against the database urls
    c = btldata.Connection()
    file_id = None
    old_url = None

    for fname in [filename] + alts:
        fetched_id, fetched_url = c.fetch_by_filename(fname)
        if fetched_id is not None:
            if file_id is not None:
                fail(f"pre-existing duplicate urls: {old_url} and {fetched_url}")
            file_id = fetched_id
            old_url = fetched_url

    if file_id is None:
        print("no matching url in btldata")
    else:
        print("found match in btldata:", file_id, old_url)

    # Figure out what session this file is from
    dw = bldw.retry_connection()
    session = dw.guess_session(h5file)
    print("this file belongs to session", session)

    # Figure out where to put this file
    session_dir = f"/datag/pipeline/{session}"
    holding_dir = f"{session_dir}/holding"
    target_filename = f"{holding_dir}/{basename}"
    if os.path.exists(target_filename):
        fail(f"a file already exists at {target_filename}")

    # Make directories
    if not os.path.exists(session_dir):
        print("mkdir", session_dir)
        os.mkdir(session_dir)
    if not os.path.exists(holding_dir):
        print("mkdir", holding_dir)
        os.mkdir(holding_dir)

    # Finally do the move
    if filename.startswith("/datag"):
        mover = "mv"
    else:
        mover = "rsync --remove-source-files -av"
    command = f"{mover} {filename} {target_filename}"
    print(command)
    subprocess.call(command.split())
    track(target_filename, dw=dw)

    if file_id is not None:
        # Update btldata
        new_url = target_filename.replace("/datag", "https://bldata.berkeley.edu")
        print(f"updating url for record {file_id} from {old_url} to {new_url}")
        c.set_url(file_id, new_url)

    # Clean up the alts
    for alt in alts:
        print("removing", alt)
        os.remove(alt)


assert __name__ == "__main__"

        
if len(sys.argv) < 2:
    fail("usage: ./safe_archive.py <filenames>")
        
names = sys.argv[1:]
for name in names:
    if os.path.isdir(name):
        for filename in glob.glob(f"{name}/*.h5"):
            safe_archive(filename)
    else:
        safe_archive(name)
        
