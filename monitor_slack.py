#!/usr/bin/python

import re
import os
import time

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
        print colored('%s:'%nodes[ln] + line, get_color(lines_ok[ln]))

def gen_lines(lines, lines_ok, nodes):
    output = ''
    for ln, line in enumerate(lines):
        if lines_ok[ln]:
            output += '        %s: %s\n'%(nodes[ln], line)
        else:
            output += '        *%s: %s*\n'%(nodes[ln], line)
    return output

observation_started = False
last_error_message = None
last_state_was_good = True
if __name__ == "__main__":
    from subprocess import check_output, STDOUT
    from termcolor import colored
    import os
    import time
    import slacker
    
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-t", "--polltime", dest="polltime", type=int, default=60,
        help="Set the polling frequency in seconds. Default: 60 s")
    parser.add_option("-S", "--simulate", dest="simulate", action="store_true", default=False,
        help="Don't sent messages to slack. Just print them to screen")
    parser.add_option("-s", "--slacklevel", dest="slacklevel", type="string", default="warning",
        help="Set Slack verbosity level. 'info'/'warning'. Default: warning")
    
    (opts, args) = parser.parse_args()
    if len(args) == 0:
        args = ["blc%d" % i for i in range(8)]
    
    N_NODES = len(args)
    
    slacklevel = opts.slacklevel.lower()
    #token = 'xoxp-18246494320-18248359968-29299072162-85d7757cf7'
    with open(os.getenv('HOME')+"/.slack_api_tester.token") as f:
        token = f.read()
    slack = slacker.Slacker(token)
    slack_chan = '#active_observations'
    if not opts.simulate:
        slack.chat.post_message(slack_chan, '*Starting slack logger. Logging level is: %s*'%slacklevel)
    else:
        print '*Starting slack logger. Logging level is: %s*'%slacklevel
    
    i = 0 # loop counter
    observation_started = False
    while(True):
        last_file_check_time = time.ctime()
        # do something grim and rife with edge case issues
        # because I'm not smart
        # enough to parse timestamps sanely.
        now = time.localtime()
        now_mins = (now.tm_hour)*60 + now.tm_min
        
        output = check_output(["/home/obs/bin/ls_last"] + args, stderr=STDOUT).split('\n')
        last_file_strs = ["*********Couldn't parse!*********"] * N_NODES
        last_file_is_ok = [False] * N_NODES
    
        for ln, line in enumerate(output):
            try:
                modtime = line.split()[7]
                h, m = map(int, modtime.split(':'))
                mins = h*60 + m
                last_file_strs[ln] = line.split(' ', 4)[-1]
                if now_mins - mins < 4:
                    last_file_is_ok[ln] = True
            except:
                pass

        last_file13_check_time = time.ctime()
        output = check_output(["/home/obs/bin/ls_latest_13"] + args, stderr=STDOUT).split('\n')
        last_file13_strs = ["*********Couldn't parse!*********"] * N_NODES
        last_file13_is_ok = [False] * N_NODES
        for ln, line in enumerate(output):
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
            except:
                pass
    
        # Now read the space on the data drives
        disk_space_check_time = time.ctime()
        output = check_output(["/home/obs/bin/df_datax"] + args, stderr=STDOUT).split('\n')
        disk_space = ["*********Couldn't parse*********"] * N_NODES
        disk_space_is_ok = [False] * N_NODES
        for ln, line in enumerate(output[1::2]):
            try:
                available = line.split()[3]
                pc_used = int(line.split()[4].rstrip('%'))
                disk_space[ln] = available
                if pc_used < 86:
                    disk_space_is_ok[ln] = True
            except:
                pass
    
        these_sources = [x.split(' ')[-1][:-14] for x in last_file_strs] #we could get this from redis. This is a whole filename without the _XXXX.XXXX.raw extension
        slack_message = ''
        if i == 0:
            slack_message += "*Available disk space on /datax (Checked at %s)*\n"%disk_space_check_time
            slack_message += gen_lines(disk_space, disk_space_is_ok, args)
            slack_message += "You won't hear from me again until there are some new files\n"
        else:
            # When sources change, send some slack info messages.
            # Always check that the previous source files closed with the correct amount of data.
            # We don't bother to check the previous file13's are for the right source. If they're not,
            # and the stale file check hasn't noticed anything, then something weird and bad is happening.
            if these_sources != last_sources:
                if observation_started == False:
                    slack_message += 'Observations have begun!\n'
                    observation_started = True
                if slacklevel == 'info':
                    slack_message += "*Beginning a new source. Latest files are (Checked at %s)*\n"%last_file_check_time
                    slack_message += gen_lines(last_file_strs, last_file_is_ok, args)
                if last_file13_is_ok == [True] * N_NODES:
                    if slacklevel == 'info':
                        slack_message += 'Previous file 12s contain the correct amount of data\n'
                else:
                    slack_message += "*Last number 12 files don't look OK (Checked at %s)*\n"%last_file_check_time
                    slack_message += gen_lines(last_file13_strs, last_file13_is_ok, args)

            if observation_started:
                # we are observing, so check files are updating ok
                if last_file_is_ok != [True] * N_NODES:
                    # print error only if the error message has changed, or this is a new error
                    # (i.e., the system has transitioned from good to bad)
                    if (last_error_message != last_file_is_ok) or (last_state_was_good):
                        last_error_message = last_file_is_ok
                        last_state_was_good = False
                        slack_message += "*Last modified files look stale (Checked at %s)*\n"%last_file_check_time
                        slack_message += gen_lines(last_file_strs, last_file_is_ok, args)
                else:
                    last_state_was_good = True
        if len(slack_message) > 0:
            if not opts.simulate:
                slack.chat.post_message(slack_chan, slack_message)
            else:
                print slack_message

        last_sources = these_sources[:]

        i += 1
        time.sleep(opts.polltime)
        
