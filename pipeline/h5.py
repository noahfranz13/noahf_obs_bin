#!/usr/bin/env python
"""
A helper for loading h5py while making sure plugins are installed and also not logging warnings.

Instead of:
import h5py
do:
from h5 import h5py
"""

import logging
logging.getLogger("hdf5plugin").setLevel(logging.ERROR)
import hdf5plugin
import h5py
