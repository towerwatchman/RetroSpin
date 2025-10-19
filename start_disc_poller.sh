#!/bin/sh

# Log file location
LOGFILE="/media/fat/retrospin/log.txt"

# Create log file directory if it doesn't exist
mkdir -p /media/fat/retrospin

# Log start of script
echo "[$(date)] Starting disc_poller" >> $LOGFILE

# Run disc_poller and redirect output (stdout and stderr) to log file
/media/fat/retrospin/disc_poller >> $LOGFILE 2>&1 &

# Store the PID of disc_poller
DISC_POLLER_PID=$!

# Log the disc_poller PID for reference
echo "[$(date)] disc_poller running with PID $DISC_POLLER_PID" >> $LOGFILE