#!/usr/bin/env python
"""
A script to repack any h5 files we can find.
This solves the problem of sessions that are generated with typically-slow chunk sizes.

Just run this script with no arguments on any blc machine with mispacked files.
"""

import os
from pathlib import Path
import subprocess

import machines

BAD_SESSIONS = [
    "AGBT21B_999_47",
    "AGBT21B_999_49",
    "AGBT21B_999_50",
    "AGBT21B_999_51",
    "AGBT21B_999_52",
    "AGBT21B_999_53",
    "AGBT22A_999_01",
    "AGBT22A_999_02",
]

assert __name__ == "__main__"

dc, host = machines.where_are_we()
assert host.startswith("blc")

def get_lines(command):
    print(command)
    return subprocess.check_output(command.split()).decode("utf-8").strip().split()

for session in BAD_SESSIONS:
    if not os.path.exists(f"/datax/dibas/{session}"):
        continue
    print("checking session", session)
    h5_files = get_lines(f"find /datax/dibas/{session}/GUPPI -maxdepth 2 -name *.h5")
    assert h5_files
    base_dir = os.path.dirname(h5_files[0])
    repack_dir = base_dir + "/repack"
    if not os.path.exists(repack_dir):
        os.mkdir(repack_dir)

    files_converted = 0
    for h5_file in h5_files:
        assert os.path.dirname(h5_file) == base_dir

        target_file = repack_dir + "/" + os.path.basename(h5_file)
        if os.path.exists(target_file):
            continue

        for line in get_lines(f"h5repack -v -l data:CHUNK=1x1x65536 {h5_file} {target_file}"):
            print(line)
        files_converted += 1

    if files_converted:
        print("done with session", session)
        Path(f"{repack_dir}/repack.done").touch()
    else:
        print("session", session, "already completed")
    
    
