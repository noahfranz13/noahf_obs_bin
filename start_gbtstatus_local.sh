#!/bin/bash

# usage: start_gbtstatus_local.sh
#
# Start guppi_gbtstatus_loop.py on the local system.  This script will refuse
# to start guppi_gbtstatus_loop.py unless run on a compute node (the output of
# `hostname -s` must start with `blc`).

HOST=$(hostname -s)

# If HOST does not start with 'blc'
if [ "${HOST#blc}" == "${HOST}" ]
then
  echo "this host (${HOST}) is not a compute node" >&2
  exit 1
fi

# Source this script to setup environment and python virtual_env
source /opt/dibas/dibas.bash

NOW=$(date)

# Rotate gbtstatus /datax logs
/usr/sbin/logrotate -s /datax/.gbtstatus_logrotate.state /opt/dibas/etc/gbtstatus_logrotate.conf |& grep -v Could.not.lock

# Create .out/.err files with current date as first line
for f in gbtstatus.{out,err}
do
  echo $NOW > /datax/$f
done

cd /datax

/usr/local/guppi_daq/bin/guppi_gbtstatus_loop.py \
  </dev/null \
  1>>gbtstatus.out \
  2>>gbtstatus.err \
  &
