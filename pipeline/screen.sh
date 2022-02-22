#!/bin/bash

STAGE=$1
TOTAL=$2

if ! [[ $STAGE =~ ^(convert|transfer|turboseti)$ ]] || ! [[ $TOTAL =~ ^[0-9]+$ ]]; then
    echo "usage: ./screen.sh <stage> <num-shards>"
    exit 1
fi

EXISTING=`screen -ls | grep $STAGE`
if [ -n "$EXISTING" ]; then
    echo there are already screens for $STAGE:
    echo $EXISTING | tr " " "\n" | grep $STAGE
    exit 1
fi

echo "try using start.sh instead of screen"
exit 1

LAST_SHARD=$((TOTAL-1))

for i in `seq 0 $LAST_SHARD`; do
    NAME=${STAGE}${i}of${TOTAL}
    echo creating screen: $NAME
    screen -d -m -S $NAME
done
