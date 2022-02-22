#!/bin/bash
# set unused banks in redis to off
# e.g. if banks 0, 1, 2, and 7 are red in cleo btl but are not currently in use:
#    ./unused_banks.sh 0..2 7
for bank in $@; do for i in blc${bank}{0..7}; do echo $i; redis-cli -h blh0 mset ${i}_observing off; done; done
