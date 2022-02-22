#!/usr/bin/env python
"""
Find archived directories for a provided text file of sessions.
Usage: ./find_archived_for_sessions.py <sessionsfile>.txt
"""

import sys

import bldw

def nice_bytes(x):
    gb = x / 1000000000
    tb = gb / 1000
    if tb >= 1:
        return f"{tb:.1f}T"
    return f"{gb:.1f}G"

assert __name__ == "__main__"

print_size = "--size" in sys.argv

dw = bldw.retry_connection()
total_size = 0
for line in open(sys.argv[1]):
    session = line.strip()
    if "#" in session:
        continue
    observations = dw.fetch_observations_for_session(session)
    if not observations:
        continue
    observation_ids = tuple(obs.id for obs in observations)
    size = dw.total_size_where("observation_id in %s AND location LIKE %s", (observation_ids, "file://pd%"))
    total_size += size
    if size > 0:
        if print_size:
            print(f"{nice_bytes(size)}\t{session}")
        else:
            print(session)
if print_size:
    print(f"{nice_bytes(total_size)} total")
