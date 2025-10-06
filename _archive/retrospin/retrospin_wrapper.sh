#!/bin/bash

# Environment from retrospin.sh
export TERM=linux
export RETROSPIN_CONSOLE="${RETROSPIN_CONSOLE:-/dev/tty2}"

# Run retrospin_launcher.py in background
python3 "/media/fat/retrospin/retrospin_launcher.py" >> "/media/fat/Scripts/retrospin_launcher.log" 2>&1