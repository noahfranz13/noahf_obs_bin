#!/usr/bin/env python

import argparse
from pipeline import convert

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert fil files to h5 files, on bls machines.")
    parser.add_argument("mounted_filename")
    parser.add_argument("--run", default=False, action="store_true")
    args = parser.parse_args()
    convert(args.mounted_filename, run=args.run)
