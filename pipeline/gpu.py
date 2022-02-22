#!/usr/bin/env python

import pipeline

assert __name__ == "__main__"

for host in pipeline.BLPC_HOSTS:
    gpu_id = -1
    print(f"\n***** host {host}:")
    for line in pipeline.run_one(host, "nvidia-smi -q -x"):
        if "<gpu id=" in line:
            gpu_id += 1
            print(f"\ngpu {gpu_id}:")
        if "<pid>" in line:
            pid = line.split("<pid>")[-1].split("</pid>")[0]
            print(f"pid: {pid}, ", end="")
        elif "<process_name>" in line:
            name = line.split("<process_name>")[-1].split("</process_name>")[0]
            print(f"process: {name}, ", end="")
        elif "<used_memory>" in line:
            used = line.split("<used_memory>")[-1].split("</used_memory>")[0]
            print(f"used: {used}")


