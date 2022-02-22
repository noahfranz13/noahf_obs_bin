#!/usr/bin/env python

import pipeline

assert __name__ == "__main__"

for host in pipeline.BLPC_HOSTS:
    stars = "*********************"
    print(stars, host, stars)
    for line in pipeline.run_one(host, "nvidia-smi"):
        print(line)
