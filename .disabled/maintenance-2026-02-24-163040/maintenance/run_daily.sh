#!/usr/bin/env bash
set -e
cd /home/joe/.openclaw/workspace
PYTHON=python3
LOGDIR=logs
mkdir -p "$LOGDIR"
DATE=$(date +"%F")
LOGFILE="$LOGDIR/maintenance-$DATE.txt"
# run the maintenance script and append output
$PYTHON maintenance/daily_maintenance.py >> "$LOGFILE" 2>&1
