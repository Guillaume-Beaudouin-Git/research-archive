#!/bin/bash
# Resume the live trader by removing the STOP kill-switch file.
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$DIR/STOP" ]; then
    rm "$DIR/STOP"
    echo "STOP file removed from $DIR — trader will resume on next run."
else
    echo "No STOP file found at $DIR/STOP — trader is already active."
fi
