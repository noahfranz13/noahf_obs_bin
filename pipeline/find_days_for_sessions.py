#!/usr/bin/env python
"""
Find the days that overlap a provided text file of sessions.
Days are printed out in mjd form.
We remove duplicates.
Usage: ./find_days_for_sessions.py <sessionsfile>.txt
"""

import sys

import bldw

dw = bldw.retry_connection()

seen = set()

for line in open(sys.argv[1]):
    session = line.strip()
    observations = dw.fetch_observations_for_session(session)

    for obs in observations:
        t = int(obs.mjd())
        if t in seen:
            continue
        seen.add(t)
        print(t, flush=True)
