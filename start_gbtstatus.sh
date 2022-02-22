#!/bin/bash

hosts="${@:-$(echo blc{0..0}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

for host in $hosts
do
  echo "starting gbtstatus_loop on $host"
  sudo ssh -o BatchMode=yes -o ConnectTimeout=1 -n -f $host "sh -c 'nohup /home/obs/bin/start_gbtstatus_local.sh'"
done
