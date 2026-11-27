#!/usr/bin/env bash
# =============================================================================
# restore_paseo.sh — minimal restore of the Paseo daemon after a sandbox reset.
# Reuses the surviving paseo + pm2 binaries; creates a NEW daemon identity
# (the old keypair was wiped with ~/.paseo), pairs via relay, writes fresh
# pairing assets to /home/z/my-project/download/, re-clones the user's repo.
# Never prints the GitHub token or the daemon password to stdout.
# =============================================================================
set -uo pipefail

export PATH="/home/z/.npm-global/bin:/home/z/.local/bin:$PATH"
export PASEO_HOME="/home/z/.paseo"
DL="/home/z/my-project/download"
PROJ="/home/z/my-project/projects"
SCRIPTS="/home/z/my-project/scripts"
mkdir -p "$PASEO_HOME" "$DL" "$PROJ"

log() { echo "[restore] $*"; }

# --- 1/6 npm globals that did not survive -----------------------------------
log "installing missing npm globals (opencode, claude-code, pnpm)..."
npm install -g --silent --no-fund --no-audit opencode-ai @anthropic-ai/claude-code pnpm >/tmp/npm_globals.log 2>&1 \
  || log "WARN: some npm globals failed (see /tmp/npm_globals.log)"
export PATH="/home/z/.npm-global/bin:/home/z/.local/bin:$PATH"
log "paseo: $(paseo --version 2>/dev/null || echo MISSING) | opencode: $(opencode --version 2>/dev/null || echo MISSING) | claude: $(claude --version 2>/dev/null || echo MISSING)"

# --- 2/6 daemon home: fresh identity + password ------------------------------
if [ -f "$PASEO_HOME/.daemon-password" ]; then
  PW=$(cat "$PASEO_HOME/.daemon-password")
else
  PW=$(python3 -c "import secrets,string;print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(20)))")
  printf '%s' "$PW" > "$PASEO_HOME/.daemon-password"
  chmod 600 "$PASEO_HOME/.daemon-password"
fi

cat > "$PASEO_HOME/config.json" <<'EOF'
{
  "daemon": { "listen": "127.0.0.1:6767", "relay": { "enabled": true } }
}
EOF

cat > "$PASEO_HOME/server.env" <<EOF
PASEO_HOME=$PASEO_HOME
PASEO_PASSWORD=$PW
PASEO_RELAY_ENABLED=true
PASEO_LOG_FILE_PATH=$PASEO_HOME/daemon.log
PASEO_LOG_FILE_LEVEL=info
PATH=/home/z/.npm-global/bin:/home/z/.local/bin:/usr/local/bin:/usr/bin:/bin
EOF
chmod 600 "$PASEO_HOME/server.env"

# --- 3/6 start under PM2 ------------------------------------------------------
pm2 delete paseo-daemon >/dev/null 2>&1 || true
cat > "$PASEO_HOME/start_daemon.sh" <<'EOF'
#!/usr/bin/env bash
set -a
. /home/z/.paseo/server.env
set +a
exec /home/z/.npm-global/bin/paseo daemon run --home /home/z/.paseo
EOF
chmod +x "$PASEO_HOME/start_daemon.sh"
pm2 start "$PASEO_HOME/start_daemon.sh" --name paseo-daemon >/dev/null 2>&1
pm2 save >/dev/null 2>&1

# --- 4/6 health check ----------------------------------------------------------
HEALTH=""
for i in $(seq 1 30); do
  sleep 2
  for ep in health api/health ""; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:6767/$ep" 2>/dev/null)
    if [ "$code" = "200" ]; then HEALTH="http://127.0.0.1:6767/$ep"; break 2; fi
  done
done
if [ -n "$HEALTH" ]; then log "daemon healthy at $HEALTH"; else log "WARN: daemon not healthy yet (continuing to pairing)"; fi

# --- 5/6 pairing via relay -----------------------------------------------------
log "pairing with relay..."
paseo daemon pair --relay --json --home "$PASEO_HOME" > "$SCRIPTS/pairing_raw.json" 2>"$SCRIPTS/pairing_err.txt" \
  || log "WARN: pair exit code $?"

# --- 6/6 repo + demo project ---------------------------------------------------
TOKEN=$(python3 - <<'PYEOF'
import json
try:
    data = json.load(open('/home/z/my-project/upload/extracted/chat.json'))
    for m in data:
        t = m.get('text','') if isinstance(m, dict) else ''
        if 'github_pat_' in t:
            i = t.find('github_pat_')
            buf = ''
            for ch in t[i:]:
                if ch.isalnum() or ch == '_':
                    buf += ch
                else:
                    break
            print(buf)
            break
except Exception:
    pass
PYEOF
)
if [ -n "$TOKEN" ]; then
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "Authorization: Bearer $TOKEN" https://api.github.com/user 2>/dev/null)
  if [ "$code" = "200" ]; then
    log "GitHub auth OK (HTTP $code) — cloning repo..."
    rm -rf "$PROJ/Paseo---Remote-Coding-Agents"
    if ! git clone --quiet "https://x-access-token:${TOKEN}@github.com/signalproofai-ux/Paseo---Remote-Coding-Agents.git" "$PROJ/Paseo---Remote-Coding-Agents" 2>/dev/null; then
      log "WARN: repo clone failed"
    else
      log "repo cloned: $(ls "$PROJ/Paseo---Remote-Coding-Agents" | wc -l) entries"
    fi
  else
    log "WARN: GitHub token rejected (HTTP $code) — probably rotated; skip clone"
  fi
else
  log "WARN: no token found in chat.json — skip clone"
fi

mkdir -p "$PROJ/demo-web"
cat > "$PROJ/demo-web/index.html" <<'EOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo Web</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main>
    <h1>Demo Web</h1>
    <p>Paseo agent sandbox project — edited live by your coding agent.</p>
  </main>
</body>
</html>
EOF
cat > "$PROJ/demo-web/styles.css" <<'EOF'
body { margin: 0; min-height: 100vh; display: grid; place-items: center;
       font-family: system-ui, sans-serif; background: #22c55e; color: #052e16; }
main { text-align: center; padding: 2rem; }
EOF
log "demo-web re-created"

log "DONE — pairing JSON at $SCRIPTS/pairing_raw.json; password at $PASEO_HOME/.daemon-password"
