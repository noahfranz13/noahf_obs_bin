#!/usr/bin/python

def get_color(good):
    if good:
        return 'green'
    else:
        return 'red'

def print_lines(lines, lines_ok):
    for ln, line in enumerate(lines):
        print colored('blc%02d: %s'%(ln, line), get_color(lines_ok[ln]))

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
    
    N_NODES = 16 
    
    while(True):
        last_file_check_time = time.ctime()
        # do something grim and rife with edge case issues
        # because I'm not smart
        # enough to parse timestamps sanely.
        now = time.localtime()
        now_mins = (now.tm_hour)*60 + now.tm_min
        
        output = check_output(["/home/obs/bin/ls_last_16"], stderr=STDOUT).split('\n')
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
            except:
                print 'Parse error:', output
                pass

        last_file13_check_time = time.ctime()
        output = check_output(["/home/obs/bin/ls_latest_13_16"], stderr=STDOUT).split('\n')
        last_file13_strs = ["Couldn't parse!"] * N_NODES
        last_file13_is_ok = [False] * N_NODES
        for ln, line in enumerate(output[:-1]):
            try:
                size = int(line.split()[4])
                last_file13_strs[ln] = line.split(' ',4)[-1]
                if size == 14093560320 or size == 14227784704:
                    last_file13_is_ok[ln] = True
            except:
                print 'Parse error:', output
                pass
    
        # Now read the space on the data drives
        disk_space_check_time = time.ctime()
        output = check_output(["/home/obs/bin/df_datax_16"], stderr=STDOUT).split('\n')
        disk_space = ["Couldn't parse"] * N_NODES
        disk_space_is_ok = [False] * N_NODES
        for ln, line in enumerate(output[1::2]):
            try:
                available = line.split()[3]
                pc_used = int(line.split()[4].rstrip('%'))
                disk_space[ln] = available
                if pc_used < 86:
                    disk_space_is_ok[ln] = True
            except:
                print 'Parse error:', output
                pass
    
        os.system("clear")
        print "Last modified files (Checked at %s)"%last_file_check_time
        print_lines(last_file_strs, last_file_is_ok)
        print ''
        print "Last number 12 files (Checked at %s)"%last_file13_check_time
        print_lines(last_file13_strs, last_file13_is_ok)
        print ''
        print "Available disk space on /datax (Checked at %s)"%disk_space_check_time
        print_lines(disk_space, disk_space_is_ok)

        if opts.polltime == 0:
            break
        else:
            time.sleep(opts.polltime)
        
