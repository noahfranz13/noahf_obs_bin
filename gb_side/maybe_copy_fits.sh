#!/bin/bash
# This script checks if we need to copy some fits stuff to the BL machines, and if we do, it does it.
# Suitable to be run in a cron job.
# You have to have `ssh bls0` set up to work correctly before running this.

set -e

DIRECTORY=`dirname $0`

echo "running maybe_copy_fits.sh at `date`"

# Don't do anything if we are observing right now.
ARE_WE_OBSERVING=`ssh bls0 /home/obs/bin/are_we_observing`
if [ "$ARE_WE_OBSERVING" == "yes" ]; then
    echo "we are currently observing. let's not copy any files now."
    exit 0
fi

if [ "$ARE_WE_OBSERVING" != "no" ]; then
    echo unexpected output from are_we_observing:
    echo $ARE_WE_OBSERVING
    echo exiting
    exit 1
fi

# Check which sessions are on the bl machines
BL_SESSIONS=`ssh bls0 'find /datax/gbtdata/2* -mindepth 1 -maxdepth 1 | cut -d/ -f5'`

# Check which sessions are on the gb machines
GB_SESSIONS=`ls /home/gbtdata | grep AGBT2.*99`

# Find which sessions are on GB but not in BL
for SESSION in `echo $BL_SESSIONS $BL_SESSIONS $GB_SESSIONS | tr " " "\n" | sort | uniq -u`; do
    if [ `$DIRECTORY/../is_bl_session $SESSION` != "yes" ]; then
	continue
    fi
    if [ `find /home/gbtdata/$SESSION -cmin -120 | wc -l` != "0" ]; then
	echo "recent files still exist in /home/gbtdata/$SESSION - let's wait a bit."
	continue
    fi

    SEMESTER=`echo $SESSION | sed 's/AGBT//' | sed 's/_.*//'`
    echo scp -q -r /home/gbtdata/$SESSION bls0:/datax/gbtdata/$SEMESTER/$SESSION
    sleep 5
    scp -q -r /home/gbtdata/$SESSION bls0:/datax/gbtdata/$SEMESTER/$SESSION
    echo copy done

    # To avoid running twice at the same time, we just do one copy per run of this script.
    exit 0
done

echo no fits files need to be copied
