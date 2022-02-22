#!/usr/bin/env python
"""
A script to clean up duplicate data on bls machines.
"""

import bldw
import datetime
import machines
import remote
import sys
import time

assert __name__ == "__main__"

def clean_h5():
    """
    Returns the number of files cleaned.
    """
    count = 0
    c = bldw.Connection()

    for gb, pd in c.fetch_duplicate_metadata():
        print()
        print("found duplicate data:")
        print("green bank:", gb.filename())
        print("berkeley:", pd.filename())
        host, filename = machines.parse_gb_filename(gb.filename())
        print(f"[{datetime.datetime.now()}] using {host} to clean up {filename}")
        remote.retry_run_one(host, f"/home/obs/bin/pipeline/safe_delete.py {filename}", hide=False, python=True)
        count += 1

    return count

def clean_x2h():
    """
    Returns the number of x2h files cleaned.
    """
    count = 0
    for m in machines.BLS_MACHINES:
        for disk in ["datax", "datax2", "datax3"]:
            x2h_folders = remote.retry_run_one(m, f"find /{disk}/pipeline -name '*.x2h' | sed 's:/[^/]*$::' | sort | uniq")
            h5_folders = remote.retry_run_one(m, f"find /{disk}/pipeline -name '*.h5' | sed 's:/[^/]*$::' | sort | uniq")
            candidates = [f for f in x2h_folders if f not in set(h5_folders)]
            for c in candidates:
                command = f"/home/obs/bin/pipeline/clean_up_x2h.sh {c}"
                print(f"running on {m}: {command}")
                for n in range(5, 0, -1):
                    print("countdown:", n)
                    time.sleep(1)
                remote.run_one(m, command, hide=False)
                count += 1
    return count

def clean_all():
    return clean_h5() + clean_x2h()

cleaner = None
if "--x2h" in sys.argv:
    cleaner = clean_x2h
elif "--h5" in sys.argv:
    cleaner = clean_h5
elif "--all" in sys.argv:
    cleaner = clean_all
else:
    raise RuntimeError(f"usage: --h5 or --x2h or --all")

prev_count = 0        
while True:
    count = cleaner()
    print(f"[{datetime.datetime.now()}] count: {count}")
    if count == 0 or count == prev_count:
        time.sleep(60)
    prev_count = count
