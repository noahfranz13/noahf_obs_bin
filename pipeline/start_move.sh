#!/bin/bash
# Starts up a worker to run a "move" for one session.
# Usage: start.sh <session>

SESSION=$1
DIR=`dirname "$(readlink -f "$0")"`

if ! [[ $SESSION =~ ^AGBT[0-9]+[A-Z]_[0-9]+_[0-9]+$ ]]; then
    echo bad session: $SESSION
    exit 1
fi

SCREEN="move_$SESSION"
EXISTING=`screen -ls | grep $SCREEN`
if [ -n "$EXISTING" ]; then
    echo there is already a screen for $SCREEN:
    echo $EXISTING | tr " " "\n" | grep $SCREEN
    exit 1
fi

echo session: $SESSION
echo creating screen: $SCREEN

# Start the screen
screen -dmS $SCREEN

# Stick commands into it
screen -S $SCREEN -X stuff "conda activate pipeline\n"
screen -S $SCREEN -X stuff "cd $DIR\n"
screen -S $SCREEN -X stuff "SESSION=$SESSION ./pipeline.py --stage=move loop 2>&1 | tee -a ~/logs/$SCREEN.log\n"
