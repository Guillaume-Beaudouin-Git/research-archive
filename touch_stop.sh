#!/bin/bash
# Halt the live trader by creating the STOP kill-switch file.
# Optionally pass a reason: ./touch_stop.sh "drawdown limit hit"
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "$1" ]; then
    echo "$1" > "$DIR/STOP"
else
    touch "$DIR/STOP"
fi
echo "STOP file created at $DIR/STOP — trader will halt on next run."
