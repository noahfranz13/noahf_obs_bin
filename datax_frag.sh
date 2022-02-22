#!/bin/bash

# Show percent used and fragmentation for /datax filesystems
# De-frag with "xfs_fsr -v /dev/sdbN"

df /datax* | \
while read fs total used avail pct mp
do
  if [ "${mp//datax/}" != "${mp}" ]
  then
    printf "%s:%s %-7s used %s, " `hostname` $fs $mp $pct
    xfs_db -rc frag $fs
  fi
done
