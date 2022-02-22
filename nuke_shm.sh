#!/bin/bash

shopt -s nullglob

# Ensure that we run as root
if [ $UID -ne 0 ]
then
  exec sudo $0 "${@}"
  # Should "never" get here
  exit 1
fi

for ipc_type in m s
do
  for i in `ipcs -$ipc_type | awk '/0x/{print $2}'`
  do
    ipcrm -$ipc_type $i
  done
done

for s in /dev/shm/sem.*
do
  pids=$(lsof -Fp $s &>/dev/null | tr -d p)
  if [ -n "${pids}" ]
  then
    echo NOT deleting active semaphore `basename $s`
    ps -fwwp ${pids}
  else
    #echo deleting semaphore `basename $s`
    rm "$s"
  fi
done
