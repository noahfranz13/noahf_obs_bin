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

#for host in $hosts
#do
#  echo "deleting shared memory and semaphores on $host"
#  ssh -o BatchMode=yes -o ConnectTimeout=1 $host /home/obs/bin/nuke_shm.sh
#done

echo -n "deleting shared memory and semaphores on the following hosts:"

i=0
for host in "$@"
do
  if [ $((i % 8)) == 0 ]
  then
    echo -ne '\n  '
  fi
  i=$((i+1))
  echo -n " $host"
  ssh -o BatchMode=yes -o ConnectTimeout=1 $host /home/obs/bin/nuke_shm.sh >& /dev/null &
done
echo
wait
