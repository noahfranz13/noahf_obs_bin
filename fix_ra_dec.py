#! /usr/bin/env python

'''
Author: M. Lebofsky (largely based on H. Isaacson's original code)
Date:   27 May 2020

Purpose: Easy updater of RA/Dec in filterbanks.

'''

from astropy.coordinates import Angle
from astropy import units as u
import os
import blimpy as bl
import os.path
import sys

if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("ra", help="ra hours (as float)")
    parser.add_argument("dec", help="dec degrees (as float)")
    parser.add_argument("file", help="filterbank file to edit")
    args = parser.parse_args()

    exists = os.path.isfile(args.file)
    if exists == False:
        print(" File Not Found: ",args.file)
        raise SystemExit

def to_sigproc_ang_format(angle_val):
    """ Convert an astropy.Angle to the ridiculous sigproc angle format string. 
        ex: RA:'17h37m48.408s',  'dec: 22d57m18s'  """
    x = str(angle_val)
    print("Angle in: ",angle_val)
    print("Angle in: ",angle_val.to_string())

    if '.' in x:
        if 'h' in x:#parse RA
            d, m, s  = int(x[0:x.index('h')]), int(x[x.index('h')+1:x.index('m')]), \
                float(x[x.index('m')+1:x.index('s')])
        if 'd' in x:#parse DEC
            d, m, s = int(x[0:x.index('d')]), int(x[x.index('d')+1:x.index('m')]), \
               float(x[x.index('m')+1:x.index('s')])
            s1,s2,s3 = 'd','m','s'
    else:
        if 'h' in x:#parse RA
            d, m, s = int(x[0:x.index('h')]), int(x[x.index('h')+1:x.index('m')]), \
               float(x[x.index('m')+1:x.index('s')])
            s1,s2,s3 = 'd','m','s'
        if 'd' in x:# parse DEC
            d, m, s = int(x[0:x.index('d')]), int(x[x.index('d')+1:x.index('m')]), \
               float(x[x.index('m')+1:x.index('s')])

    str_out = str(d*1.e4+m*100.+s )+'000'
    max_dlen = 3
    str_out = str_out[0:str_out.index('.')+4] 

    print("Output", str_out)
    return str_out

# Read in the header from the data file.
fb = bl.Waterfall(args.file, load_data=False)
fb_ra = fb.header['src_raj']
fb_dec= fb.header['src_dej'] #format: '22d57m18s'

# Run the command lines to actually change the header
temp_ra = args.ra
temp_dec = args.dec
raj_ang = Angle(temp_ra,u.hour)
dec_ang = Angle(temp_dec,u.deg)

new_raj = to_sigproc_ang_format(raj_ang)
new_dec = to_sigproc_ang_format(dec_ang)

line_out = args.file+","+str(fb_ra.hour)+','+str(fb_dec.deg)+','+str(temp_ra)+','+str(temp_dec)

print('file,ra_in,dec_in,ra_out,dec_out')
print(line_out)

cmd = "/home/obs/bin/headeredit_wrapper %s -src_raj %s -src_dej %s" % (args.file,new_raj,new_dec)
print("Command: %s" % cmd)
os.system(cmd) 
print(' Changed header ra,dec values from',fb_ra.value, fb_dec.value,' to ',raj_ang.hour,dec_ang.deg)
