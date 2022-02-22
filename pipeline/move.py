#!/usr/bin/env python

import argparse
from pipeline import move

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move fil files from blc machines to bls machines.")
    parser.add_argument("source_host")
    parser.add_argument("source_dir")
    parser.add_argument("target_host")
    parser.add_argument("target_disk")
    parser.add_argument("--run", default=False, action="store_true")
    args = parser.parse_args()
    move(args.source_host, args.source_dir, args.target_host, args.target_disk, run=args.run)
