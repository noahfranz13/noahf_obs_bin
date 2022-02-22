#!/usr/bin/env python

import os
import sys

def h5_manifest_csv(directory):
    """
    Create a manifest csv from the h5 files in a current directory.
    Each line is filename,filesize where the name is just the basename.
    Lines are alphabetized by filename.
    """
    filenames = os.listdir(directory)
    for fname in filenames:
        if fname.endswith(".fil"):
            raise RuntimeError(f"{directory} not ready for manifest because it contains {fname}")
    h5s = [f for f in filenames if f.endswith(".h5")]
    h5s.sort()
    print("measuring...", flush=True)
    lines = []
    for h5 in h5s:
        size = os.path.getsize(os.path.join(directory, h5))
        line = f"{h5},{size}"
        print(line)
        lines.append(line + "\n")
    return "".join(lines)


def validate(directory):
    """
    Raises an exception if the manifest does not validate.
    This probably means a corrupted copy.
    If some files are missing, they have probably already been copied out.
    """
    csv = h5_manifest_csv(directory)
    existing_lines = set(line.strip() for line in open(os.path.join(directory, "zmanifest.csv")))
    for line in csv.strip().split("\n"):
        if line not in existing_lines:
            raise IOError(f"file does not match manifest: {line}")

    
if __name__ == "__main__":
    d = sys.argv[1]
    print("creating manifest for", d)
    csv = h5_manifest_csv(d)
    if "--nowrite" not in sys.argv:
        with open(os.path.join(d, "zmanifest.csv"), "w") as f:
            f.write(csv)
            f.close()
    print("manifest created")
