#!/bin/bash

# Ensure that we run as root
if [ $UID -ne 0 ]
then
  exec sudo $0 "${@}"
  # Should "never" get here
  exit 1
fi

hosts="${@:-$(echo blc{0..7}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

SCRIPT='/opt/dibas.*/player_main.py'

for host in $hosts
do
  echo "killing player(s) on $host"
  ssh -o BatchMode=yes -o ConnectTimeout=1 $host "
    pkill -INT  -f 'python ${SCRIPT}'
    sleep 1
    pkill -TERM  -f 'python ${SCRIPT}'
    sleep 1
    pkill -KILL  -f 'python ${SCRIPT}'
  " &
done
