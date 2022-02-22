#!/bin/bash

# usage: start_player_local.sh [-s] NAME
#
# Start a player with the given NAME on the local system.  If `-s` is given
# (before NAME) then the player will be started in simulate mode.  This script
# will refuse to start players unless run on a compute node (the output of
# `hostname -s` must start with `blc`).

# Refuse to run unless we're root
if [ $UID -ne 0 ]
then
  echo "error: must be root, not $(whoami)" >&2
  exit 1
fi

HOST=$(hostname -s)

# If HOST does not start with 'blc'
if [ "${HOST#blc}" == "${HOST}" ]
then
  echo "error: this host (${HOST}) is not a compute node" >&2
  exit 1
fi

SIM=''
VERBOSE=''
# Parse options
while getopts 'sv' OPT
do
  case "${OPT}" in
    s) SIM='-s'
      ;;
    v) VERBOSE='-v'
      ;;
    ?) exit 1
      ;;
  esac
done
shift $((OPTIND-1))

player="${1}"

NOW=$(date)

# Rotate BLP /datax logs
#/usr/sbin/logrotate -s /datax/.blp_logrotate.state /opt/dibas/etc/blp_logrotate.conf |& grep -v Could.not.lock

# Create .out/.err files with current date as first line
for f in ${player}.{out,err}
do
  echo $NOW > /datax/$f
done

cd /datax

# Allow player (and its subprocesses to generate core files)
ulimit -c unlimited

/opt/dibas/bin/player ${VERBOSE} -n ${player} -b ${SIM} \
  </dev/null \
  1>>${player}.out \
  2>>${player}.err \
  &
