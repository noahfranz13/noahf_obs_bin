#!/bin/bash

sim=''
if [ "$1" == '-s' ]
then
  sim='-s'
  shift
fi

hosts="${@:-$(echo blc{0..0}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

for host in $hosts
do
  player=${host/blc/BLP}

  echo "starting player ${player} on $host"
  sudo ssh  -o BatchMode=yes -o ConnectTimeout=1 -n -f $host "sh -c 'cd /datax; taskset -c 7-11 nohup /opt/dibas/bin/player -v -n ${player} -b $sim </dev/null >${player}.out 2>${player}.err &'"
done
