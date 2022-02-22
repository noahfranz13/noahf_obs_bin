#!/usr/bin/env python
"""
Find collated directories for a provided text file of sessions.
"""

import collate
import sys

assert __name__ == "__main__"

find_size = "--size" in sys.argv
total_kb = 0
for line in open(sys.argv[1]):
    session = line.strip()
    if "#" in session:
        continue
    d = collate.find_collate_dir(session)
    if not d:
        continue
    if find_size:
        kb = collate.dir_kb(d)
        total_kb += kb
        print(collate.nice_kb(kb), d)
    else:
        print(d)
        
if find_size:
    print(collate.nice_kb(total_kb), "total")
