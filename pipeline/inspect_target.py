#!/usr/bin/env python
"""
A script to display information about a target.
"""
import sys

import bldw
from h5 import h5py

assert __name__ == "__main__"

target_name = sys.argv[1]

c = bldw.Connection()

targets = c.fetch_targets_by_name(target_name)

if len(targets) > 1:
    print(f"**************** multiple targets are named {target_name} ****************")

for target in targets:
    print()
    print(target)
    print("sessions with relevant data:")
    obs = c.fetch_observations_by_target(target.id)
    for ob in obs:
        tags = c.fetch_tags_for_observation_id(ob.id)
        for tag in tags:
            if tag.name.startswith("AGBT"):
                print(tag.name)
