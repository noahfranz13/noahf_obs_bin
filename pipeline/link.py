#!/usr/bin/env python
"""
A script to add missing file -> scan connections.
"""

import bldw

def main():
    c = bldw.Connection()
    fixed = 0
    for m in c.fetch_iter_metadata("observation_id IS NULL"):
        try:
            obs = c.guess_observation_by_timestamp(m.timestamp())
        except LookupError:
            # There really is no observation that matches. Okay
            continue

        # We found a missing link
        print("fixing:")
        print(m)
        print("to point to:")
        print(obs)
        m.observation_id = obs.id
        c.update_meta_observation_id(m)
        fixed += 1
        print(f"done. fixed metadata for {fixed} files")
        print()
            
    
if __name__ == "__main__":
    main()
