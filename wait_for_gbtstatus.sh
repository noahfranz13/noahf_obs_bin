#!/bin/bash

expected_count=${1:?usage: $(basename $0) EXPECTED_COUNT}

projids_present=
projids_ok=

# Sleep for progressively longer delays
for delay in {1..10}
do
  projids_present=
  projids_ok=

  projid_count=`guppidaq_redis_grep.rb PROJID | wc -l`
  # If, for some reason, projid_count is empty, use 0
  if [ ${projid_count:-0} -lt $((expected_count)) ]
  then
    echo "waiting for $((expected_count - ${projid_count:-0})) PROJID values"
    sleep $delay
    continue
  fi
  projids_present=1

  junk_count=`guppidaq_redis_grep.rb PROJID | grep -c JUNK`
  # If, for some reason, junk_count is empty, use expected_count
  if [ ${junk_count:-${expected_count}} -ne 0 ]
  then
    echo "waiting for ${junk_count:-${expected_count}} PROJID=JUNK to clear"
    sleep $delay
    continue
  fi
  projids_ok=1

  break
done

if [ -z "${projids_present}" ]
then
  echo "TIMEOUT waiting for $expected_count PROJID values"
  exit 1
fi

if [ -z "${projids_ok}" ]
then
  echo "TIMEOUT waiting for ${junk_count:-${expected_count}} PROJID=JUNK to clear"
  exit 1
fi
