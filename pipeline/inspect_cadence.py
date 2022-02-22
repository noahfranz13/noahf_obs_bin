#!/usr/bin/env python
"""
A script to display information about a cadence.
"""

import sys

import bldw
import machines

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: ./inspect_cadence.py <cadence-id> [<frequency>]")
        sys.exit(1)

    dw = bldw.retry_connection()
    cadence_id = int(sys.argv[1])

    cadence = dw.fetch_cadence(cadence_id)
    cadence.populate_metas(dw)
    cadence.show()
    
    for freq in cadence.representative_freqs():
        print()
        aligned = cadence.align_metas(freq)
        if not aligned:
            print(f"frequency {freq} does not have enough data for alignment")
            continue
        print(f"frequency {freq}:")
        for metas in aligned:
            print()
            for m in metas:
                print(m.filename())
    print()
