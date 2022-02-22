#!/usr/bin/env python

import pipeline

assert __name__ == "__main__"

for i, host in enumerate(pipeline.BLPC_HOSTS):
    if i > 0:
        print()
    print("host:", host)
    for line in pipeline.run_one(host, "ps aux | grep turboSET | grep ^obs | grep -v grep || true"):
        print(line)
