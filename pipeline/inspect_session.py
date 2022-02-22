#!/usr/bin/env python
"""
A tool to show information about some sessions.

Usage:

./inspect_session.py
shows information for the most recent few sessions

./inspect_session.py <session-id-list>
shows information about a list of sessions
"""

import bldw
import bltargets
from datetime import datetime
import os
import remote
import sys


def inspect_session(session, conn):
    """
    Returns a list of directories that have files relevant to this session.
    Returns an empty list if this session is not ready.
    """
    observations = conn.fetch_observations_for_session(session)
    start_time = min(ob.start_time for ob in observations)
    print(f"{len(observations)} scans in {session}, starting at {datetime.utcfromtimestamp(start_time)}")
    cadences = conn.fetch_cadences_for_session(session)
    cadences = [c for c in cadences if c.is_abacad()]
    print(f"{session} has {len(cadences)} abacad cadences:")
    print(", ".join(str(cad.id) for cad in cadences))

    if session == "AGBT22A_999_03":
        # Matt moved this one, it belongs to someone else, but is mistakenly tagged as a session in bldw
        filenames = []
    else:
        filenames = remote.retry_run_one("bls0", f"find /mnt_blc*/datax*/dibas/{session} -name '*.raw' -o -name '*.h5'")
    h5_count = 0
    dirs = set()
    for filename in filenames:
        if "DIAG" in filename:
            continue
        if filename.endswith(".raw") and "/blc" in filename:
            print(f"{filename} still needs to be reduced.")
            return []
        if filename.endswith(".h5"):
            h5_count += 1
            dirs.add(os.path.dirname(filename))

    if not h5_count:
        print("no h5 files found.")
        return []

    print(f"{h5_count} h5 files, in directories:")
    return list(sorted(dirs))


if __name__ == "__main__":
    conn = bldw.retry_connection()
    args = sys.argv[1:]
    
    if args:
        sessions = args
    else:
        sessions = conn.all_sessions()
        sessions.reverse()
        sessions = sessions[:3]
        
    for session in sessions:
        print()
        for d in inspect_session(session, conn):
            print(d)
    print()



