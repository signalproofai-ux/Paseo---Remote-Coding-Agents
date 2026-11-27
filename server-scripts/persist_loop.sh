#!/usr/bin/env bash
# persist_loop.sh — run persist_backup.sh every 5 minutes (PM2-managed).
export PATH="/home/z/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
while true; do
  bash /home/z/my-project/scripts/persist_backup.sh >> /home/z/my-project/.state/persist_loop.log 2>&1
  sleep 300
done
