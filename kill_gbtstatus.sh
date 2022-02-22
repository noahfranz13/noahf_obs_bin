#!/bin/bash

hosts="${@:-$(echo blc{0..7}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

SCRIPT='/usr/local/guppi_daq/bin/guppi_gbtstatus_loop.py'

for host in $hosts
do
  echo "killing gbtstatus_loop(s) on $host"
  sudo ssh -o BatchMode=yes -o ConnectTimeout=1 $host "
    pkill -INT  -f 'python ${SCRIPT}'
    sleep 1
    pkill -TERM  -f 'python ${SCRIPT}'
    sleep 1
    pkill -KILL  -f 'python ${SCRIPT}'
  " &
done

wait
