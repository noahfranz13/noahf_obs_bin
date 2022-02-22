#!/usr/bin/env python
"""
A script to output information from all cadences from the database.
The format is one json string per line, one line for each cadence.
Only considers ABACAD cadences.
"""

import bldw
from cadence import good_cadences_for_session
import json
import remote
import sys

assert __name__ == "__main__"

dw = bldw.retry_connection()
sessions = remote.retry_run_one("blpc0", "ls /datag/pipeline")
sessions = [s for s in sessions if s > "AGBT19"]
sessions.sort()

for session in sessions:
    cadences = dw.fetch_cadences_for_session(session)
    for cadence in good_cadences_for_session(dw, session):
        freqs = cadence.representative_freqs()
        print(f"frequencies for cadence {cadence.id} in {session}: {freqs}", file=sys.stderr)
        for freq in freqs:
            for metas in cadence.align_metas(freq):
                filenames = [m.filename() for m in metas]
                assert len(filenames) == 6
                data = {
                    "id": cadence.id,
                    "freq": freq,
                    "filenames": filenames,
                }
                print(json.dumps(data))
