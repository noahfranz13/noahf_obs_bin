#!/usr/bin/env python
"""
Create peti configuration files.
For now, the assumption is that we are handling one session at a time.

Usage:
./configure_peti.py <session>
"""
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sys

import bldw
from inspect_session import inspect_session
from schedule_scraper import Scraper

assert __name__ == "__main__"

conn = bldw.retry_connection()
session = sys.argv[1]

# First, clear all configs
config_dir = os.path.expanduser("~/peticonfig")
existing = os.listdir(config_dir)
if existing:
    print(f"clearing {len(existing)} configs in", config_dir)
    for f in existing:
        os.remove(os.path.join(config_dir, f))
    print("configs cleared")

# See how much time we have available. Leave a little buffer
buffer_hours = 2
scraper = Scraper()
hours = min(24, scraper.free_hours()) - buffer_hours
if hours <= 0:
    print(scraper)
    print("the cluster is in use. not configuring anything")
    sys.exit(0)
stop = datetime.now(timezone.utc) + timedelta(hours=hours)
    
dirs = inspect_session(session, conn)
if not dirs:
    print("session is not ready for peti. not configuring anything")
    sys.exit(0)

# We expect to only see each machine once
seen_machines = set()

for mounted_dir in dirs:
    m = re.fullmatch("/mnt_(blc[0-9]{2})(/datax.*/dibas/AGBT.*/GUPPI/BLP[0-9]{2})", mounted_dir)
    machine = m.group(1)
    local_dir = m.group(2)
    assert machine not in seen_machines
    seen_machines.add(machine)

    data = json.dumps({
        "machine": machine,
        "directories": [local_dir],
        "stop": stop.isoformat(),
        }, indent=2)
    config_filename = f"{config_dir}/{machine}.json"
    with open(config_filename, "w") as f:
        f.write(data + "\n")
    print(f"wrote config for {mounted_dir} to {config_filename}")
    
