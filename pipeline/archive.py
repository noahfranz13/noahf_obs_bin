#!/usr/bin/env python

import argparse
from pipeline import archive

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move h5 to their long-term home.")
    parser.add_argument("directory")
    parser.add_argument("--run", default=False, action="store_true")
    args = parser.parse_args()
    archive(args.directory, run=args.run)
