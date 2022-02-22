#!/usr/bin/env python
"""
A script to find incorrect file -> scan connections.
The plan was to actually fix incorrect file -> scan connections, but we didn't find any.
"""

import bldw

def main():
    c = bldw.Connection()
    count = 0
    for row in c.fetch_iter("""
      SELECT * from bl.data INNER JOIN bl.observation ON data.observation_id = observation.id
      WHERE abs((data.tstart - 40587) * 86400 - observation.start_time) > 20
      """):
        assert len(row) == 24
        m = bldw.Metadata.from_row(row[:17])
        obs = bldw.Observation.from_row(row[-7:])

        print(m.strtime(), m.location)
        print(obs)
        tags = c.fetch_tags_for_observation_id(obs.id)
        print("metadata time:", (m.tstart - 40587) * 86400)
        print("obs time:", obs.start_time)
        for tag in tags:
            print(tag.name)
        print()
        
        count += 1
        if count >= 10:
            return
            
    
if __name__ == "__main__":
    main()
