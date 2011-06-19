#!/bin/bash

################################################################################
# Script to:
#    0. set up NOVA environment
#    1. allocate a public IP
#    2. associate the IP with this instance
#    3. mount the /data share
################################################################################

# time between attempts (seconds)
SLEEPTIME=15


# first, source the NOVA stuff
. /home/ubuntu/.nova/novarc

# get a public IP and allocate to this instance
IP=$(euca-allocate-address | awk '{ print $2}')
while true; do
    echo "Doing: euca-associate-address -i $HOSTNAME $IP"
    OUT=$(euca-associate-address -i $HOSTNAME $IP)
    echo "$OUT"
    if ! echo "$OUT" | grep -i "error" >/dev/null 2>&1; then
        break
    fi
    sleep $SLEEPTIME
done

# mount the /data share
while true; do
    if OUT=$(mount -t nfs dcnfs.nci.org.au:/short/w85 /data 2>&1); then
        echo "/data has been mounted"
        break
    fi
    if echo "$OUT" | grep -i "already mounted" >/dev/null 2>&1; then
        echo "/data already mounted"
        break
    fi
    echo "$OUT"
    sleep $SLEEPTIME
done
