#!/usr/bin/python

import re

# Ts is ADC sample time
Ts = 1/3e9
# Tc is coarse channel sample time
Tc = 1024 * Ts
# Tblk is time per data block (512K spectra)
Tblk = 512 * 1024 * Tc
# Bblk is the number of bytes per data block
# 512K spectra x 64 channels x 2 pols x (1+1) re+im
Bblk = 512 * 1024 * 64 * 2 * (1+1)
# Nblk is number of blocks per "full" data file
Nblk = 128
# Ttot is total expected time per scan in seconds (hard coded here to 5 mintues)
Ttot = 60 * 5

def get_color(good):
    if good:
        return 'green'
    else:
        return 'red'

def print_lines(lines, lines_ok, nodes):
    for ln, line in enumerate(lines):
        print colored('%s: %s'%(nodes[ln], line), get_color(lines_ok[ln]))

def print_lines8(lines, lines_ok, nodes):
    i = 0
    for ln, line in enumerate(lines):
        if i % 8 != 0:
          print '  ',
        print colored('%s: %s'%(nodes[ln], line), get_color(lines_ok[ln])),
        i = i + 1
        if i % 8 == 0:
          print

if __name__ == "__main__":
    from subprocess import check_output, STDOUT
    from termcolor import colored
    import os
    import time
    
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-t", "--polltime", dest="polltime", type=int, default=60,
        help="Set the polling frequency in seconds. Default: 60 s")
    
    (opts, args) = parser.parse_args()
    if len(args) == 0:
        args = ["blc%d" % i for i in range(8)]
    
    N_NODES = len(args)
    
    while(True):
        last_file_check_time = time.ctime()
        # do something grim and rife with edge case issues
        # because I'm not smart
        # enough to parse timestamps sanely.
        now = time.localtime()
        now_mins = (now.tm_hour)*60 + now.tm_min
        
        output = check_output(["/home/obs/bin/ls_last"] + args, stderr=STDOUT).split('\n')
        last_file_strs = ["Couldn't parse!"] * N_NODES
        last_file_is_ok = [False] * N_NODES
    
        for ln, line in enumerate(output[:-1]):
            try:
                modtime = line.split()[7]
                h, m = map(int, modtime.split(':'))
                mins = h*60 + m
                last_file_strs[ln] = line.split(' ', 4)[-1]
                if now_mins - mins < 2:
                    last_file_is_ok[ln] = True
            except Exception as e:
                print 'Parse error:', output
                print e
                pass

        last_file13_check_time = time.ctime()
        output = check_output(["/home/obs/bin/ls_latest_13"] + args, stderr=STDOUT).split('\n')
        last_file13_strs = ["Couldn't parse!"] * N_NODES
        last_file13_is_ok = [False] * N_NODES
        for ln, line in enumerate(output[:-1]):
            try:
                size = int(line.split()[4])
                last_file13_strs[ln] = line.split(' ',4)[-1]
                nfull_files = int(re.sub('.*(\d\d\d\d).raw$', '\\1', line), 10)
                nblk_last = size // Bblk # Use Python's silly "//" integer divide operator
                nblks = Nblk * nfull_files + nblk_last
                total_time = Tblk * nblks
                delta_time = total_time - Ttot
                last_file13_strs[ln] += ' (%+.3f s)' % delta_time
                if abs(delta_time) <= 8: # should be Tblk, but relax for now due to known limitations
                    last_file13_is_ok[ln] = True
            except Exception as e:
                print 'Parse error:', output
                print e
                pass
    
        # Now read the space on the data drives
        disk_space_check_time = time.ctime()
        output = check_output(["/home/obs/bin/df_datax"] + args, stderr=STDOUT).split('\n')
        disk_space = ["Couldn't parse"] * N_NODES
        disk_space_is_ok = [False] * N_NODES
        for ln, line in enumerate(output[1::2]):
            try:
                available = line.split()[3]
                pc_used = int(line.split()[4].rstrip('%'))
                disk_space[ln] = available
                if pc_used < 86:
                    disk_space_is_ok[ln] = True
            except Exception as e:
                print 'Parse error:', output
                print e
                pass
    
        os.system("clear")
        print "Last modified files (Checked at %s)"%last_file_check_time
        print_lines(last_file_strs, last_file_is_ok, args)
        print ''
        print "Last number {12,13,14} files (Checked at %s)"%last_file13_check_time
        print_lines(last_file13_strs, last_file13_is_ok, args)
        print ''
        print "Available disk space on /datax (Checked at %s)"%disk_space_check_time
        print_lines8(disk_space, disk_space_is_ok, args)

        if opts.polltime == 0:
            break
        else:
            time.sleep(opts.polltime)
        
