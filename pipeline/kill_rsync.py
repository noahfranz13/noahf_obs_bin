#!/usr/bin/env python

import machines
import remote

assert __name__ == "__main__"

for host in machines.BLS_MACHINES:
    print("killing rsync on", host, flush=True)
    remote.run_one(host, "ps aux | grep ^obs | grep rsync | grep -v grep | grep include=pipeline | awk '{print $2}' | xargs kill -9")
