#!/usr/bin/env bash
set -eo pipefail
RIPDISC_PATH=/media/fat/dla/cdrdao

# Do this to wait for the drive to be ready
# Try to get a disc label
DISCNAME=`lsblk -n -o LABEL /dev/sr0 | sed 's/(.*)/$1/'`
if [ -z "$DISCNAME" ]; then
	DISCNAME=unknown
fi
echo Ripping $DISCNAME
# Dump the disc and convert the toc to cue
${RIPDISC_PATH}/cdrdao read-cd --read-raw --datafile $DISCNAME.bin --device /dev/sr0 --driver generic-mmc-raw $DISCNAME.toc
${RIPDISC_PATH}/toc2cue $DISCNAME.toc $DISCNAME.cue