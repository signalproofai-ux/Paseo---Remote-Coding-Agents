#!/usr/bin/env bash
# guard.sh — lightweight resource + service watchdog (PM2-managed, 60s loop).
# Append-only log with rotation at 2MB. This host has NO swap and NO sudo,
# so OOM protection must stay observational + preventive (heap caps are set
# in the daemon start script); guard records pressure before things die.
export PATH="/home/z/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
LOG="/home/z/my-project/.state/guard.log"
while true; do
  TS=$(date -u '+%Y-%m-%d %H:%M:%S')
  LOAD=$(cut -d' ' -f1 /proc/loadavg)
  MEMAV=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  DISK=$(df -P / | awk 'NR==2{gsub(/%/,"");print $5}')
  HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:6767/api/health 2>/dev/null)
  PM2N=$(pm2 jlist 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print(','.join(f\"{p['name']}={p['pm2_env']['status']}\" for p in d))
except Exception: print('pm2-unavailable')")
  echo "$TS load=$LOAD memAvailMB=$MEMAV disk%=$DISK daemonHealth=$HEALTH pm2[$PM2N]" >> "$LOG"
  if [ "$DISK" -ge 85 ]; then echo "$TS CRITICAL: disk usage ${DISK}% — manual cleanup required" >> "$LOG"; fi
  if [ "$MEMAV" -lt 400 ]; then echo "$TS CRITICAL: <400MB RAM available — OOM risk (no swap on host)" >> "$LOG"; fi
  [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 2097152 ] && tail -c 1000000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  sleep 60
done
