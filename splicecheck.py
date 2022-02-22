#!/usr/bin/env python
"""
splicecheck.py

Fix GBT filterbank files with missing banks
S. Croft 2017 July 18
"""

import blimpy as bl
import argparse
import re
from collections import OrderedDict
import numpy as np
from sys import exit

def append_to_filterbank(filename, data, n_bytes=4):
    """ Append data to an existing filterbank file """
    with open(filename, "a") as fileh:
            if n_bytes == 4:
#                np.float32(data[:, ::-1].ravel()).tofile(fileh)
                np.float32(data[0][:, ::-1].ravel()).tofile(fileh)
            elif n_bytes == 2:
                np.int16(data[0][:, ::-1].ravel()).tofile(fileh)
#                np.int16(data[:, ::-1].ravel()).tofile(fileh)
            elif n_bytes == 1:
                np.int8(data[0][:, ::-1].ravel()).tofile(fileh)
#                np.int8(data[:, ::-1].ravel()).tofile(fileh)

def fix_header(fb,nbo,ncpb):
    print "Fixing header..."
    fb.header['nchans'] = nbo * ncpb
    return fb

def fix_data(fb, ncpb, fixbanks, nbankso):
    print "Fixing data..."
    for i in range (0,8):
#        print "Bank "+str(i)
        if fixbanks["0"+str(i)] == True:
            print " - Fixing bank 0"+str(i)
            fb.data = np.insert(fb.data, nbankso - (ncpb * i), np.zeros(ncpb))
            newsize = fb.data.size
            fb.data = fb.data.reshape(1,1,newsize)
    return fb

def fix_filterbank(filename, filename_out, nbo, ncpb, fixbanks):
    # Load just the filterbank header
    fb = bl.Filterbank(filename, load_data=False)

    # Read first integration
    t = 0
    fb.read_filterbank(fb.filename, f_start=None, f_stop=None,
                       t_start=t, t_stop=t+1, load_data=True)

    fb = fix_header(fb,nbo,ncpb)
    #fb = fix_data(fb,ncpb,fixbanks)
    # write the header - don't use write_to_filterbank method
    # because it computes nchans from the input data
    with open(filename_out, "w") as fileh:
        fileh.write(bl.sigproc_header.generate_sigproc_header(fb))

    # Loop through time integrations
    for t in range(1, fb.n_ints_in_file):
        fb.read_filterbank(fb.filename, f_start=None, f_stop=None,
                           t_start=t, t_stop=t+1, load_data=True)
        fb = fix_data(fb,ncpb,fixbanks,nbo)
        append_to_filterbank(filename_out, fb.data)
        print "** Integration "+str(t)

def main():
    parser = argparse.ArgumentParser(description="Fix filterbank files with missing banks")
    parser.add_argument('filename',help="Filename")
    args = parser.parse_args()

    #filename = "/Users/scroft/Dropbox/spliced_blc0001020304050607_guppi_57774_72191_LHS1140_0006.gpuspec.0002.fil"
    filename = args.filename
    m = re.match('(.*spliced_blc).*(_guppi.*)',filename)
    if not m:
        exit("ERROR: "+filename+" does not appear to be a spliced filterbank file")

    f = bl.Filterbank(filename, load_data = False)

    # dictionary to hold whether or not a given bank is present
    banks = OrderedDict()
    for i in range(0,8):
        banks["0"+str(i)] = False

    # dictionary to hold which banks need fixing
    fixbanks = OrderedDict()
    for i in range(0,8):
        fixbanks["0"+str(i)] = False

    # lowest and highest banks present in input
    lowbank = 0
    highbank = 0
    # check the filename for the presence of these banks
    for bank in banks:
        m = re.search('spliced_blc.*('+re.escape(bank)+').*_guppi',filename)
        if m:
            banks[bank] = True
            highbank = int(bank)
            if not lowbank:
                lowbank = int(bank)

    # loop through the banks, and set lower_bank_present if there are data present in a lower bank.
    # We only care about cases where there are banks missing in the middle (e.g. TTTFFTTT);
    # we don't care about cases where just the upper banks are missing (e.g. TTTTTTFF)
    # or just the lower banks are missing (e.g. FFFTTTTT).
    # In the latter case, we'll output five banks, which we count with the variable nbanksout
    nbanksout = 0
    bank_out_string = ""

    for bank in banks.items():
        if (not bank[1]) and int(bank[0]) >= lowbank and int(bank[0]) <= highbank:
            print "Bank "+bank[0]+" missing; will zero pad."
            fixbanks[bank[0]] = True
            bank_out_string += 'zz'
            nbanksout += 1
        elif bank[1]:
            bank_out_string += bank[0]
            print "Bank "+bank[0]+" present."
            nbanksout += 1
        else:
            print "Bank "+bank[0]+" missing; will not zero pad."
            bank_out_string += 'xx'

    # set output filename
    m = re.match('(.*spliced_blc).*(_guppi.*)',filename)
    out_filename = m.group(1)+bank_out_string+m.group(2)

    # read some info from the filterbank header
    nchans = f.header['nchans']
    fstep = -f.header['foff']*1e6
    header_bandwidth = nchans * fstep / 1e9
    nbanks = sum(banks.itervalues())
    nchans_per_bank = nchans / nbanks
    file_bandwidth = nbanks * 0.1875
    fixit = False
    if file_bandwidth == header_bandwidth:
        filestat = "appear to be in agreement."
    else:
        filestat = "appear to not be in agreement."
        fixit = True
    if file_bandwidth < 1.5:
        filestat += " Some banks appear to be missing."
        fixit = True

    print "The filename implies %d banks, and so I expect a total bandwidth %.3f GHz.\nThe filterbank header specifies %d channels "\
       "of width %.2f Hz for a total bandwidth %.3f GHz.\nThe filename and header %s" \
       % (nbanks, file_bandwidth, nchans, fstep, header_bandwidth, filestat)

    if fixit:
        fix_filterbank(filename, out_filename, nbanksout, nchans_per_bank, fixbanks)
        print "Wrote "+out_filename
    else:
        print "Input file checks out OK and was not rewritten."

if __name__=="__main__":

    main()
