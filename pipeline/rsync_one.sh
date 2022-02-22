#!/bin/bash

COMMAND="rsync -avW --block-size=16384 $1 rsync://blpd18.ssl.berkeley.edu/datax/"
echo $COMMAND
$COMMAND
