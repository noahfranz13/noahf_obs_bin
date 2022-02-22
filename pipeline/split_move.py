#!/usr/bin/env python
"""
This script is designed to move a large directory of collated files into several smaller directories.
Example usage:
./split_move.py /datax AGBT19A_999_69 

This will move files out of /datax/collate/AGBT19A_999_69 and into /datax/pipeline/AGBT19A_999_69/collate0, collate1, etc.
"""

import os
import re
import shutil
import sys

assert __name__ == "__main__"
drive = sys.argv[1]
session = sys.argv[2]

assert re.fullmatch("/datax[0-9]?", drive)
assert re.fullmatch("AGBT[0-9AB]+_[0-9]+_[0-9]+", session)

def move_to_new_dir(files, new_dir):
    """
    Creates a new directory and moves stuff there.
    Paths are absolute.
    """
    assert not os.path.exists(new_dir)
    os.mkdir(new_dir)
    for f in files:
        shutil.move(f, new_dir)
    print(f"done moving stuff to {new_dir}")
    open(new_dir + "/move.done", "w").close()

# Group up the files to avoid going over tb_limit in each group when possible
tb_limit = 3.0
complete_groups = []
current_group = []
source = f"{drive}/collate/{session}"
target_root = f"{drive}/pipeline/{session}"
total_tb = 0.0
for f in os.listdir(source):
    if not f.endswith("fil"):
        continue
    if "DIAG" in f:
        continue
    full = f"{source}/{f}"
    size = os.path.getsize(full)
    tb_size = size / 1_000_000_000_000
    if total_tb + tb_size > tb_limit:
        complete_groups.append((total_tb, current_group))
        current_group = []
        total_tb = 0.0
    current_group.append(full)
    total_tb += tb_size
complete_groups.append((total_tb, current_group))

# Do the copying
assert complete_groups
if len(complete_groups) == 1:
    names = ["collate"]
else:
    names = [f"collate{i}" for i in range(len(complete_groups))]
if not os.path.exists(target_root):
    os.mkdir(target_root)
for (tb, group), name in zip(complete_groups, names):
    dest = f"{target_root}/{name}"
    print(f"{len(group)} files add up to {tb:.2f}T, to put in {dest}")
    move_to_new_dir(group, dest)
