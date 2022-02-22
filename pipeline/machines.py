#!/usr/bin/env python
"""
Tools that help do tasks specific to the Green Bank and Berkeley machines.
"""
from functools import lru_cache
import os
import re
import socket
import sys

# Two-letter datacenter codes
GREEN_BANK = "gb"
BERKELEY = "pd"

HEAD = "blh0"
GREEN_BANK_MACHINES = [HEAD] + [f"bls{i}" for i in range(10)] + [f"blc{x}{y}" for x in range(8) for y in range(8)]
BERKELEY_MACHINES = [HEAD] + [f"blpc{i}" for i in range(3)] + [f"blpd{i}" for i in range(20)]

BLS_MACHINES = [m for m in [f"bls{n}" for n in range(10)]]

@lru_cache
def where_are_we():
    """
    Returns a (datacenter code, machine name) tuple.
    Guesses which datacenter we are in heuristically if it has to.
    """
    host = socket.gethostname()

    # Normal machines in berkeley
    if host not in GREEN_BANK_MACHINES:
        assert host in BERKELEY_MACHINES
        assert in_berkeley()
        return (BERKELEY, host)

    # Normal machines in green bank
    if host not in BERKELEY_MACHINES:
        assert not in_berkeley()
        return (GREEN_BANK, host)
    
    # We inconveniently name some hosts the same. Tiebreak by looking at directory names
    if in_berkeley():
        return (BERKELEY, host)
    else:
        return (GREEN_BANK, host)

def assert_dc_host(expected_dc, expected_host):
    """
    Raise an exception if we are not on the expected datacenter and host.
    """
    dc, host = where_are_we()
    if dc != expected_dc:
        raise RuntimeError(f"this code expects to run in {expected_dc} but we are in {dc}")
    if host != HEAD:
        raise RuntimeError(f"this code expects to run on {expected_host} but we are on {host}")

def assert_green_bank_head():
    assert_dc_host(GREEN_BANK, HEAD)

def assert_berkeley_head():
    assert_dc_host(BERKELEY, HEAD)
    
def in_berkeley():
    """
    A heuristic for figuring out if we are in Berkeley.
    """
    return os.path.isdir("/home/obs/obs_bin")

def to_location(filename, datacenter=None):
    """
    Constructs the canonical file:// location from a datacenter and filename.
    If datacenter is not provided, uses the current one and treats this filename like a local file.
    """
    if datacenter is None:
        datacenter, host = where_are_we()
        if filename.startswith("/datax"):
            filename = f"/mnt_{host}" + filename
    if datacenter == GREEN_BANK:
        match = re.fullmatch(r"/mnt_([a-z0-9]+)/(.*)", filename)
        if match is None:
            raise ValueError(f"filename does not look like a mount: {filename}")
        machine = match[1]
        if machine not in GREEN_BANK_MACHINES:
            raise ValueError(f"unrecognized green bank machine: {machine}")
        return f"file://{GREEN_BANK}-{machine}/{match[2]}"

    if datacenter == BERKELEY:
        match = re.fullmatch(f"/datag/(.*)", filename)
        if match is None:
            raise ValueError(f"filename does not look like gluster: {filename}")
        return f"file://{BERKELEY}-datag/{match[1]}"

    raise ValueError(f"unrecognized datacenter: {datacenter}")


def from_location(location):
    """
    Returns a (datacenter, filename) pair based on a file:// location.
    """
    match = re.fullmatch(r"file://([a-z]{2})-([a-z0-9]+)/(.*)", location)
    if match is None:
        raise ValueError(f"unrecognized location: {location}")
    dc = match[1]
    machine = match[2]
    rest = match[3]
    if dc == GREEN_BANK:
        assert machine in GREEN_BANK_MACHINES
        return dc, f"/mnt_{machine}/{rest}"
    if dc == BERKELEY:
        assert machine == "datag"
        return BERKELEY, f"/datag/{rest}"
    raise ValueError(f"unrecognized datacenter: {dc}")

def parse_gb_filename(filename):
    """
    Returns a (host, local filename) pair for a /mnt filename.
    """
    match = re.fullmatch(r"/mnt_([a-z0-9]+)(/.*)", filename)
    if match is None:
        raise ValueError(f"unparseable filename: {filename}")
    host = match[1]
    local_filename = match[2]
    assert host in GREEN_BANK_MACHINES
    return host, local_filename


if __name__ == "__main__":
    dc, host = where_are_we()
    print("you are in the", dc, "datacenter")
    print("this machine is", host)
    for filename in sys.argv[1:]:
        loc = to_location(dc, filename)
        print(filename, "corresponds to location", loc)
        new_dc, new_filename = from_location(loc)
        assert new_dc == dc
        assert new_filename == filename
