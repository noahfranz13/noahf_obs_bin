#!/usr/bin/env python

import manifest
import os
import sys

if __name__ == "__main__":
    d = sys.argv[1]
    print("validating manifest for", d)
    manifest.validate(d)
    print("manifest is valid")
