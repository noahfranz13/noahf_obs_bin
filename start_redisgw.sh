#!/bin/bash

hosts="${@:-$(echo blc{0..0}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

for host in $hosts
do
  echo "starting guppidaq_redis_gateway on $host"
  sudo ssh  -o BatchMode=yes -o ConnectTimeout=1 -n -f $host /usr/local/bin/guppidaq_redis_gateway.rb
done
