#!/usr/bin/env python
"""
This script is outside the regular pipeline since it's more like a one-off script used to move files into
the right location for the regular pipeline.
"""

import collate
import machines
import os
import random
import remote


DIR = os.path.dirname(os.path.realpath(__file__))


def move(mounted_dir):
    host, source_dir = machines.parse_gb_filename(mounted_dir)
    remote.run_one(host, f"find {source_dir} -name '*.fil' -size -2k -delete")
    nothing, drivename, collate, session = source_dir.split("/")
    assert not nothing
    assert collate == "collate"
    move_cmd = f"/home/obs/bin/pipeline/split_move.py /{drivename} {session}"
    
    print(f"{host}: {move_cmd}")
    remote.run_one(host, move_cmd, hide=False, python=True)


def du0(mounted_dir):
    host, local_dir = machines.parse_gb_filename(mounted_dir)
    remote.run_one(host, f"du -ach --max-depth=0 {local_dir}", hide=False)

def get_sessions():
    return [line.strip() for line in open(f"{DIR}/collate_first.txt")]
    
def random_collate_dir():
    sessions = get_sessions()
    random.shuffle(sessions)
    for s in sessions:
        d = collate.find_collate_dir(s)
        if d:
            print(d)
            du0(d)
            return d
    raise ValueError("no collate dirs left")

def find_total_remaining_size():
    sessions = get_sessions()
    total = 0
    for s in sessions:
        d = collate.find_collate_dir(s)
        if not d:
            continue
        kb = collate.dir_kb(d)
        total += kb
        print(f"{nice_kb(kb)}\t{d}", flush=True)
    print("total:", collate.nice_kb(total))
        
