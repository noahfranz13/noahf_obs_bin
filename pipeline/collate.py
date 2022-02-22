#!/usr/bin/env python
"""
Utilities for analyzing directories of collated files.
"""

import machines
import remote

def find_collate_dir(session):
    """
    Returns a mounted filename of a directory containing collated fil files for the given session.
    Returns None if there is none.
    Raises an error if there are multiple.
    """
    find_cmd = f"find /mnt_bls*/datax*/collate/ -maxdepth 1 -name '*{session}'"
    dirnames = remote.retry_run_one("bls0", find_cmd)
    answers = []
    for dirname in dirnames:
        count_cmd = f"ls {dirname}/*.fil | grep -v DIAG | wc -l"
        count = int(remote.retry_run_one("bls0", count_cmd)[0])
        if count > 0:
            answers.append(dirname)
    if not answers:
        return None
    assert len(answers) == 1, str(answers)
    return answers[0]

def dir_kb(mounted_dir):
    """
    Return the size of this directory in kilobytes.
    """
    host, local_dir = machines.parse_gb_filename(mounted_dir)
    lines = remote.retry_run_one(host, f"du -ac --max-depth=0 {local_dir}")
    size = int(lines[-1].split()[0])
    return size

def nice_kb(kb):
    """
    A printable string for an amount of kilobytes
    """
    return f"{kb/1000000000.0:.1f}T"


