#!/bin/bash

hosts="${@:-$(echo blc{0..7}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

for host in $hosts
do
  echo "killing guppidaq_redis_gateway(s) on $host"
  sudo ssh -o BatchMode=yes -o ConnectTimeout=1 $host 'pkill -TERM -f "/usr/local/bin/ruby /usr/local/bin/guppidaq_redis_gateway.rb"'
done
