#!/usr/bin/env python

import argparse
from pipeline import transfer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transfer h5 files from Green Bank (gb) to Berkeley (pd)")
    parser.add_argument("directory")
    parser.add_argument("--run", default=False, action="store_true")
    args = parser.parse_args()
    transfer(args.directory, run=args.run)
