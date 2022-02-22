#/usr/local/bin/python
 
from astropy.io import fits
import numpy as np
import pandas as pd
import os
import sys

'''
    Purpose: Examine fits files stored by the GBT, and use the extracted 
            information to cross check Breakthrough Listen data 
            
    Date:  12 May 2017
    
    Author: H. Isaacson

    Notes: There are auxilliary fits files stored at the GBT in 
            /home/archive/science-data/16B/AGBT16B_999_25/
            where 16B is the semester and the 25 is the 
            session ID for that semester and project.
            
    Usage  > python3.7 bl_open_fits.py -d /home/archive/science-data/16B/AGBT16B_999_25/Antenna/ -f 2016_09_19_15:55:14.fits         
            
'''


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-f","--file",type = str,help = 'Enter Filename')
    parser.add_argument("-d","--dir", type = str,help = 'Enter Directory')
#    parser.add_argument("-t","--test",type=bool,default = True, help = "Set as True to run a single session. ")
    args = parser.parse_args()
    
    
# Test file name:
# filename='/home/archive/science-data/16B/AGBT16B_999_25/Antenna/2016_09_19_15:55:14.fits'

if args.dir == None:
    inDIR='/home/archive/science-data/16B/AGBT16B_999_25/Antenna/'
else:
    inDIR=args.dir
        
if args.file == None:
    testfile='2016_09_19_15:55:14.fits'
    filename = inDIR + testfile
else:
    filename = inDIR + args.file 
    
# Test if file exists:
if os.path.exists(filename):
  exist = 1
else: 
  print("File not found:"+filename) 
  sys.exit()

# Create a function to open the fits files and return SINGLE values for mjd,ra,dec
def open_gofits(filename):
    hdulist = fits.open(filename,memmap=None)      
    hd = hdulist[0].header
    hd_data = hdulist[2].data
    
    if len(hd_data.field(0)) != 0:
        df = pd.DataFrame(hd_data)
        df2 = df.copy()
        del df2['REFRACT']
        del df2['MAJOR']
        del df2['MINOR']
        del df2['OBSC_AZ']
        del df2['OBSC_EL']
        del df2['SR_XP']
        del df2['SR_YP']
        del df2['SR_ZP']
        del df2['SR_XT']
        del df2['SR_YT']
        del df2['SR_ZT']
    else:
        df=0
    hdulist.close()
    return df, df2 #hd_mjd,hd_ra,hd_dec
    
df, df2 = open_gofits(filename)

ra = df['RAJ2000'].median()
dec = df['DECJ2000'].median()
az = df2['MNT_AZ'].median()
el = df2['MNT_EL'].median()

#out = pd.Series([ra,dec,az,el])
print(ra,dec,az,el)
#head1='ra,dec,az,el \n'
#outstr= str(ra)+','+str(dec)+','+str(az)+','+str(el)
#f = open('out.csv', 'w')
#f.write(head1)
#f.write(outstr)
#f.close()
