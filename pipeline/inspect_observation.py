#!/usr/bin/env python
"""
A script to display information about an observation.
"""

import sys

import bldw
import machines

def main():
    args = sys.argv[1:]
    if not args:
        print("usage: ./inspect_observation.py <id>")
        sys.exit(1)

    obs_id = int(sys.argv[1])

    c = bldw.Connection()
    obs = c.fetch_observation(obs_id)
    print(obs)
    target = c.fetch_target(obs.target_id)
    print(target)
    metas = c.fetch_metadata_by_observation_id(obs_id)
    for m in metas:
        if m.deleted:
            continue
        if not m.location.endswith("0000.h5"):
            continue
        print(m)

if __name__ == "__main__":
    main()
