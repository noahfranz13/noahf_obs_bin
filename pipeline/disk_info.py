#!/usr/bin/env python
"""
Tools for analyzing disk information
"""

import machines
import remote

class DiskInfo(object):
    """
    Create a handy object from a line of df output.
    "Terabytes" here is measured in powers-of-two which might explain slight differences.
    """
    def __init__(self, line):
        parts = line.split()
        assert len(parts) == 6
        fs, blocks, used, avail, used_pct_str, self.mount = parts
        self.root_dir = "/" + self.mount.split("/")[-1]
        self.host = fs.split("-")[0]
        self.avail_tb = int(avail) / (2 ** 30)
        self.used_pct = int(used_pct_str.strip("%"))        

    def __str__(self):
        return f"{self.mount} has {self.avail_tb:.1f}T available"

def find_available(pattern):
    """
    Returns a list of DiskInfo showing free space for Green Bank machines.
    """
    machines.assert_green_bank_head()
    command = f"df /mnt_{pattern}/datax*"
    # print("running", command, flush=True)
    lines = remote.retry_run_one("bls0", command)
    answer = []
    for line in lines:
        if line.startswith("Filesystem"):
            continue
        info = DiskInfo(line)
        if not info.mount.startswith("/mnt_"):
            continue
        if info.host == "blc18" and info.root_dir == "/datax":
            # This one has the wrong directory structure, so skip it here
            continue
        answer.append(info)
    return answer
    
def gluster_tb():
    """
    Returns how much TB of space is left in gluster.
    """
    machines.assert_berkeley_head()
    lines = remote.retry_run_one("blpc0", f"df /datag | grep /datag")
    if not lines:
        raise RuntimeError("cannot see gluster")
    if len(lines) > 1:
        raise RuntimeError("we can see multiple glusters?")
    info = DiskInfo(lines[0])
    return info.avail_tb
