#!/usr/bin/env python
"""
A script to clean up directories after the h5 files have been moved out.

Usage: ./clean_up_incoming.py <dirname>
"""
import os
import sys

def clean(dirname):
    dirname = os.path.normpath(dirname)

    if not os.path.isdir(dirname):
        raise IOError(f"path is not a directory: {dirname}")

    contents = os.listdir(dirname)
    for filename in contents:
        if filename != "zmanifest.csv":
            raise IOError(f"directory {dirname} cannot be cleaned because it contains {filename}")
        os.remove(os.path.join(dirname, filename))

    # Recursively remove any empty directories, up to a "pipeline" or "incoming" directory
    while True:
        if dirname.endswith("incoming") or dirname.endswith("pipeline"):
            print(f"leaving {dirname} in place for future incoming files")
            return
        if os.listdir(dirname):
            print(f"leaving {dirname} in place because it is not empty")
            return
        print(f"removing empty directory {dirname}")
        os.rmdir(dirname)
        dirname = os.path.dirname(dirname)
        
    
if __name__ == "__main__":
    if len(sys.argv) == 0:
        print("usage: track.py <filename> [flags]")
        sys.exit(1)
    flags = []
    for arg in sys.argv[2:]:
        if arg not in flags:
            print("unrecognized arg:", arg)
            sys.exit(1)
            
    dirname = sys.argv[1]
    clean(dirname)
