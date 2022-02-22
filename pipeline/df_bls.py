#!/usr/bin/env python
"""
A script to check available disk space on bls machines.
"""

import machines
import remote

assert __name__ == "__main__"

for m in machines.BLS_MACHINES:
    print(m)
    remote.retry_run_one(m, "df -h | grep ' /datax'", hide=False)
