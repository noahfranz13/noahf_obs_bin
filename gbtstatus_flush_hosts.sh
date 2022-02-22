#!/bin/bash

echo Sending the flush-hosts command to the GBT status database
echo `date` Sending the flush-hosts command to the GBT status database >> /datax/gbtstatus_flush_hosts.log
mysqladmin -h gbtdata.gbt.nrao.edu -u gbtstatus --password=w3bqu3ry flush-hosts

