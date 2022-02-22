#!/usr/bin/env python
from h5 import h5py

def check_valid(h5file):
    data = h5file["data"]
    print("data shape:", data.shape)
    data[0]
    if data.shape[0] > 1:
        data[1]
        data[-1]

    
