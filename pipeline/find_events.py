#!/usr/bin/env python
"""
A script to find events.
Usage: find_events.py <cadence_id> <frequency> <output_directory>
"""

import os
import shutil
import sys
import tempfile

import bldw

print("importing turboseti...", flush=True)
from turbo_seti.find_event.find_event_pipeline import find_event_pipeline


assert __name__ == "__main__"

args = sys.argv[1:]
if len(args) < 3:
    print("usage: ./find_events.py <cadence_id> <frequency> <output_dir>")
    sys.exit(1)
cadence_id = int(args[0])
freq = int(args[1])
output_dir = args[2].rstrip("/")
assert output_dir
if os.path.exists(output_dir):
    raise RuntimeError(f"events output directory already exists: {output_dir}")

print("connecting to database...", flush=True)
dw = bldw.Connection()
cadence = dw.fetch_cadence(cadence_id)
cadence.populate_metas(dw)
cadence.show()

metas = cadence.metas_for_event_stage(freq)
assert metas
print("finding events from .h5 files:")
for m in metas:
    print(m.filename())
    assert os.path.exists(m.filename())
print("using corresponding .dat files:")
for m in metas:
    print(m.dat_filename().replace("/home/obs", "~"))

temp_dir = tempfile.mkdtemp()

# find_event_pipeline assumes that everything is in the same directory.
# We don't want to actually keep everything in the same directory, we want to leave the input files where they are while generating
# files into a temporary directory.
# So we create a bunch of symlinks in the temporary directory.
h5_symlinks = []
dat_symlinks = []
for m in metas:
    h5_base = os.path.basename(m.filename())
    dat_base = os.path.basename(m.dat_filename())
    h5_symlink = os.path.join(temp_dir, h5_base)
    dat_symlink = os.path.join(temp_dir, dat_base)
    os.symlink(m.filename(), h5_symlink)
    os.symlink(m.dat_filename(), dat_symlink)
    h5_symlinks.append(h5_symlink)
    dat_symlinks.append(dat_symlink)

# find_event_pipeline only accepts lists of files in the form of a .lst file.
dat_list_path = os.path.join(temp_dir, "dat_files.lst")
with open(dat_list_path, "w") as f:
    for name in dat_symlinks:
        f.write(name + "\n")
print("created", dat_list_path)

csv_path = os.path.join(temp_dir, "found_event_table.csv")
find_event_pipeline(dat_list_path, filter_threshold=3, number_in_cadence=len(metas), csv_name=csv_path, saving=True)

# The run was a success. Copy the files over to the intended output dir
event_dir = os.path.dirname(output_dir)
if not os.path.exists(event_dir):
    print(f"creating directory {event_dir}")
    os.mkdir(event_dir)
print(f"moving output from {temp_dir} to {output_dir}")
shutil.move(temp_dir, output_dir)
