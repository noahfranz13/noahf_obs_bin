#!/usr/bin/env python

import random
import threading
import pipeline

SEARCH_ID = "ts1"
PY_ENV = "source /opt/conda/etc/profile.d/conda.sh && conda activate pipeline &&"


def search(host, h5_filename):
    output_base = f"/mnt_bls0/datax/pipeline/{SEARCH_ID}"
    partial = h5_filename.split("/pipeline/")[1].rsplit("/", 1)[0]
    output_dir = f"{output_base}/{partial}"
    cmd = f"/home/obs/bin/pipeline/turboseti.sh {h5_filename} {output_dir}"
    print(f"[{host}] {cmd}", flush=True)
    result = pipeline.run_one(host, f"{PY_ENV} {cmd}")
    for line in result:
        print(f"[{host}] {line}")
    print(f"[{host}] task complete", flush=True)


def keep_searching(host, queue):
    while queue:
        print(f"{len(queue)} tasks remaining")
        if pipeline.should_stop():
            print(f"stopping {host}...")
            return
        filename = queue.pop()
        search(host, filename)


def main():
    hosts = pipeline.BLS_HOSTS
    files = [f for f in pipeline.find_searchable(SEARCH_ID) if "0001" not in f]
    print(f"found {len(files)} input files", flush=True)

    threads = [threading.Thread(target=keep_searching, args=(host, files)) for host in hosts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print("done")

    
if __name__ == "__main__":
    main()

