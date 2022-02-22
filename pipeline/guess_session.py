#!/usr/bin/env python

import os
import sys

import bldw
from h5 import h5py

filename = sys.argv[1]
c = bldw.retry_connection()
h5file = h5py.File(filename, "r")
print(c.guess_session(h5file))
