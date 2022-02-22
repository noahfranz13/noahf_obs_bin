#!/usr/bin/env python
"""
Given a list of targets, find a list of sessions that have observations of one (or more) of these targets.
"""

import bldw
import sys

assert __name__ == "__main__"

filename = sys.argv[1]
assert filename.endswith("txt")

sessions = set()
dw = bldw.Connection()

for line in open(filename):
    target_name = line.strip()
    targets = dw.fetch_targets_by_name(target_name)
    if not targets:
        continue
    for target in targets:
        obs = dw.fetch_observations_by_target(target.id)
        for ob in obs:
            tags = dw.fetch_tags_for_observation_id(ob.id)
            for tag in tags:
                if tag.name.startswith("AGBT"):
                    sessions.add(tag.name)
    print("processed", target_name, file=sys.stderr)
                    
for session in sorted(list(sessions)):
    print(session)
