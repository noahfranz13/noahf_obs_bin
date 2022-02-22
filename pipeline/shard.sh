#!/bin/bash

NAME=$(echo $STY | sed 's/.*\.//')

if [ -z "$NAME" ]
then
    echo "we are not running in a shard-screen"
    exit 1
fi

echo shard detected: $NAME
CMD="./pipeline.py --shard=auto $*" 
echo running: $CMD "2>&1 | tee -a ~/logs/$NAME.log"
$CMD 2>&1 | tee -a ~/logs/$NAME.log
