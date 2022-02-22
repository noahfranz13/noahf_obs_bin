#!/bin/bash

set -e

echo checking $1 for cleaning x2h files...
COUNT_H5=`find $1 -name '*.h5' | wc -l`

if [[ $COUNT_H5 -ne "0" ]]
then
    echo there are $COUNT_H5 .h5 files in $1
    exit 1
fi

echo zero .h5 files in $1

COUNT_X2H=`find $1 -name '*.x2h' | wc -l`
if [[ $COUNT_X2H -eq "0" ]]
then
    echo there are no .x2h files here to clean
    exit 1
fi

echo $COUNT_X2H .x2h files can be cleaned up
echo find $1 -name '*.x2h' -delete
find $1 -name '*.x2h' -delete

