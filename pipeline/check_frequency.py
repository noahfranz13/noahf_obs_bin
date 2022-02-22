#!/usr/bin/env python
# Checks whether a directory of files is invalid because the telescope
# is just reporting garbage at these frequency ranges.

# WARNING: this logic is only correct for Green Bank! Don't apply this to files from other telescopes.

import bldw
import blimpy
import machines
import os
import shutil
import sys

# I am aware of three different sources for the valid band ranges. All disagree with each other.
# 1. https://arxiv.org/pdf/2101.11137.pdf (https://files.slack.com/files-pri/T0J78EJ9E-F02D6M9UH9N/image.png)
# 2. https://www.gb.nrao.edu/scienceDocs/GBTog.pdf (https://files.slack.com/files-pri/T0J78EJ9E-F02CH7GBLKV/image.png)
# 3. The "chain" script in this repo. mattl: "based on ad hoc meetings and internal discussions".
# To be conservative, any frequency that any of these sources considers to be valid, this code considers to be valid.
VALID_BANDS = {
    "L": (1025, 1925),
    "S": (1730, 2720),
    "C": (3950, 8200),
    "X": (7800, 11200),
}

# Some bands have multiple receiver-names in the database they can correspond to
BAND_NAMES = {
    "Rcvr1_2": "L",
    "Rcvr2_3": "S",
    "Rcvr4_6": "C",
    "Rcvr4_8": "C",
    "Rcvr8_10": "X",
    "Rcvr8_12": "X",
}

def in_interval(value, interval):
    low, high = interval
    assert low < high
    return low <= value <= high

def file_matches_band(filename, band):
    wf = blimpy.Waterfall(filename=filename, load_data=False)

    f_begin = wf.header["fch1"] - (wf.header["foff"] / 2)
    f_end = f_begin + wf.header["nchans"] * wf.header["foff"]
    f_interval = tuple(sorted([f_begin, f_end]))

    # If either endpoint of the file is valid, the file is useful.
    if in_interval(f_begin, band) or in_interval(f_end, band):
        return True

    # Theoretically a file could entirely contain a valid band.
    if in_interval(band[0], f_interval):
        return True

    return False


def guess_session(dirname):
    parts = dirname.split("/")
    for part in parts:
        if "GBT" in part:
            return part
    raise ValueError(f"cannot guess session from directory name: {directory}")


def check_directory(dirname):
    """
    Returns whether this directory looks like we can continue processing it.
    """
    assert os.path.isdir(dirname)
    conn = bldw.Connection()
    
    session = guess_session(dirname)
    observations = conn.fetch_observations_for_session(session)
    rec_ids = set(obs.receiver_id for obs in observations)
    if not rec_ids:
        raise ValueError(f"there are no observations for session {session}")
    if len(rec_ids) > 1:
        print(f"there are multiple receivers for session {session}")
        return True
    
    rec = conn.fetch_receiver(rec_ids.pop())
    letter = BAND_NAMES[rec.name]
    print(f"this data should be {letter}-band")
    band = VALID_BANDS[letter]
    print(f"the valid frequency range is {band}")

    # Compare to the files
    filecount = 0
    for subdir, _, basenames in os.walk(dirname):
        for basename in basenames:
            # Only check h5 and fil files
            if not basename.endswith(".h5") and not basename.endswith(".fil"):
                continue
            filename = os.path.join(subdir, basename)
            if file_matches_band(filename, band):
                if filecount > 0:
                    print(f"the first {filecount} files checked were invalid.")
                print(f"{filename} is in the valid frequency range.")
                return True
            filecount += 1

    assert filecount > 0
    print(f"{filecount} files in {dirname} are all outside of the valid frequency range")

    left, right = dirname.split("/dibas")
    last_dir = right.split("/")[-1]
    invalid_dir = f"{left}/invalid"
    new_dir = f"{invalid_dir}/{session}_{last_dir}"
    print(f"moving {dirname} to {new_dir}", flush=True)
    assert os.path.isdir(invalid_dir)
    shutil.move(dirname, new_dir)
    print("move done")
    return False

    
if __name__ == "__main__":
    dirname = sys.argv[1]
    print("checking frequency:", dirname)

    # Other scripts will check this last line, so don't mess with it
    if check_directory(dirname):
        print("OK")
    else:
        print("INVALID")
