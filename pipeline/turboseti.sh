#!/bin/bash

# This wrapper script runs turboseti on a single file and puts
# all output files as well as stdout.log in a single newly-created output directory.
# This will refuse to output files into a directory if the directory is already there.
# Usage: turboseti.sh <input file> <output directory> <gpu id>

if [ -z "$3" ]
then
    echo Usage: turboseti.sh [input file] [output directory] [gpu id]
    exit 1
fi

if [ -d "$2" ]
then
    echo "Directory $2 already exists."
    exit 1
fi

mkdir -p `dirname $2`

DIR=`mktemp -d`

if [ ! -f "$1" ]; then
    echo "file does not exist: $1"
    exit 1
fi

echo [`date`] "prechecking..."

/home/obs/obs_bin/pipeline/precheck_turboseti.py $1

if [ $? -ne 0 ]; then
    echo [`date`] "precheck failed. skipping this file"
    mkdir $2
    echo "precheck failed" > $2/stdout.log
    exit 0
fi

MAX_DRIFT=4
SNR=10

echo [`date`] "running turboseti in" $DIR "on" `hostname` "GPU" $3
echo [`date`] "running:" CUDA_DEVICE_ORDER=PCI_BUS_ID "CUDA_VISIBLE_DEVICES="$3 turboSETI $1 "--max_drift" $MAX_DRIFT "--snr" $SNR "-g y -o" $DIR

CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=$3 turboSETI $1 --max_drift $MAX_DRIFT --snr $SNR -g y -o $DIR > $DIR/stdout.log 2> $DIR/stderr.log

if [ $? -ne 0 ]; then
    echo [`date`] "turboseti run failed."
    cat $DIR/stderr.log
    exit 1
fi

echo [`date`] "turboseti run succeeded."

# Check if the output is over 100M
KILOBYTES=`du -s $DIR | cut -f1`
if [ "$KILOBYTES" -gt "100000" ]; then
    echo [`date`] "the output is too large, though."
    rm $DIR/*

    # Create fake output to replace the too-large real output.
    # We need to create a stdout so the pipeline knows not to rerun this,
    # and we create toolarge.log to indicate what happen in a find/greppable way.
    echo "output too large" > $DIR/stdout.log
    echo "output too large" > $DIR/stderr.log
fi

# Remove stderr.log if it's empty
find $DIR -name "stderr.log" -size 0 -delete

sleep 1
echo [`date`] moving files to $2
mv $DIR $2
chmod a+rx $2
echo [`date`] done
