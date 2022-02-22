#!/bin/bash

NAME=$(echo $STY | sed 's/.*\.//')

if [ "$NAME" != "archive" ]
then
    echo "we are not running in the archive shard-screen"
    exit 1
fi


CMD="./pipeline.py --stage=archive watch"
echo running: $CMD "2>&1 | tee -a ~/logs/$NAME.log"
$CMD 2>&1 | tee -a ~/logs/$NAME.log
