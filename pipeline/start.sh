#!/bin/bash
# Starts up workers to run one stage of the pipeline in screens.
# Runs in "watch" mode.
# Usage: start.sh <stage> <num-shards>

STAGE=$1
SHARDS=$2
DIR=`dirname "$(readlink -f "$0")"`

if ! [[ $STAGE =~ ^(move|convert|transfer|archive|turboseti|events)$ ]] || ! [[ $SHARDS =~ ^[0-9]+$ ]]; then
    echo "usage: ./start.sh <stage> <num-shards>"
    exit 1
fi

EXISTING=`screen -ls | grep $STAGE`
if [ -n "$EXISTING" ]; then
    echo there are already screens for $STAGE:
    echo $EXISTING | tr " " "\n" | grep $STAGE
    exit 1
fi

if [[ "$STAGE" == "move" ]]; then
    MODE=watch
else
    MODE=watch
fi

echo stage: $STAGE
echo shards: $SHARDS
echo mode: $MODE
LAST_SHARD=$((SHARDS-1))

for i in `seq 0 $LAST_SHARD`; do
    NAME=${STAGE}${i}of${SHARDS}
    echo creating screen: $NAME

    # Start the screen
    screen -dmS $NAME

    # Stick commands into it
    screen -S $NAME -X stuff "conda activate pipeline\n"
    screen -S $NAME -X stuff "cd $DIR\n"
    screen -S $NAME -X stuff "./pipeline.py --shard=auto $MODE 2>&1 | tee -a ~/logs/$NAME.log\n"
done
