#!/usr/bin/env python

import pipeline
import remote

assert __name__ == "__main__"

for host in pipeline.BLPC_HOSTS:
    print("killing turboseti on", host, flush=True)
    remote.run_one(host, "ps aux | grep ^obs | grep turboSETI | grep -v grep | awk '{print $2}' | xargs kill -9")
