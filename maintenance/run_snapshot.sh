#!/usr/bin/env bash
set -e
cd /home/joe/.openclaw/workspace
/usr/bin/env python3 maintenance/snapshot_status.py >> logs/snapshot.log 2>&1
