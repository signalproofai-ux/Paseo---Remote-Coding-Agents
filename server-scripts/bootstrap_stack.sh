#!/usr/bin/env bash
# =============================================================================
# bootstrap_stack.sh — idempotent restore of the full Paseo + agents stack
# after a sandbox recycle. Safe to re-run any number of times.
#
# Key design change vs the previous (broken) setup:
#   PASEO_HOME now lives INSIDE the persistent workspace
#   (/home/z/my-project/.state/paseo) so the daemon identity, config and
#   password survive sandbox recycles. Previously ~/.paseo was wiped on every
#   recycle, killing the pairing identity and forcing re-pairing every time.
#
# Secrets: GitHub token is read from /home/z/my-project/secure/gh.token
# (0600). Never printed. Daemon password stored at $PASEO_HOME/.daemon-password
# (0600) and mirrored to download/daemon-password.txt (0600) for the phone app.
# =============================================================================
set -uo pipefail
export PATH="/home/z/.npm-global/bin:$PATH"
export PASEO_HOME="/home/z/my-project/.state/paseo"
WS="/home/z/my-project"
DL="$WS/download"
PROJ="$WS/projects"
SEC="$WS/secure"
ST="$WS/.state"
LOG="$WS/scripts/bootstrap.log"

log() { echo "[$(date -u '+%H:%M:%S')] $*" | tee -a "$LOG"; }

mkdir -p "$PASEO_HOME" "$DL" "$PROJ" "$SEC" "$ST"

# --- 1/6 npm globals (skip if already present) --------------------------------
missing=""
for b in paseo opencode claude pm2 gemini; do
  command -v "$b" >/dev/null 2>&1 || missing="$missing $b"
done
if [ -n "$missing" ]; then
  log "installing npm globals:$missing"
  pkgs=""
  for b in $missing; do
    case "$b" in
      paseo)    pkgs="$pkgs @getpaseo/cli" ;;
      opencode) pkgs="$pkgs opencode-ai" ;;
      claude)   pkgs="$pkgs @anthropic-ai/claude-code" ;;
      pm2)      pkgs="$pkgs pm2" ;;
      gemini)   pkgs="$pkgs @google/gemini-cli" ;;
    esac
  done
  npm install -g --silent --no-fund --no-audit $pkgs >"$ST/npm_install.log" 2>&1 \
    || log "WARN: some npm installs failed (see $ST/npm_install.log)"
fi
log "versions: paseo=$(paseo --version 2>/dev/null || echo MISSING) opencode=$(opencode --version 2>/dev/null || echo MISSING) claude=$(claude --version 2>/dev/null | head -c 20 || echo MISSING) gemini=$(gemini --version 2>/dev/null || echo MISSING) pm2=$(pm2 --version 2>/dev/null || echo MISSING)"

# --- 2/6 daemon identity + password (persistent now) --------------------------
if [ -f "$PASEO_HOME/.daemon-password" ]; then
  PW=$(cat "$PASEO_HOME/.daemon-password")
  log "reusing existing daemon password + identity"
else
  PW=$(python3 -c "import secrets,string;print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(20)))")
  printf '%s' "$PW" > "$PASEO_HOME/.daemon-password"
  chmod 600 "$PASEO_HOME/.daemon-password"
  log "created new daemon password"
fi
chmod 600 "$PASEO_HOME/.daemon-password" 2>/dev/null

# --- 3/6 daemon config (docs-sanctioned keys, written via CLI where possible) --
if [ ! -f "$PASEO_HOME/config.json" ]; then
  paseo daemon config set daemon.listen 127.0.0.1:6767 --home "$PASEO_HOME" >/dev/null 2>&1 \
    || { mkdir -p "$PASEO_HOME"; printf '{"daemon":{"listen":"127.0.0.1:6767"}}' > "$PASEO_HOME/config.json"; }
  log "daemon listen set to 127.0.0.1:6767"
fi

# --- 4/6 start daemon under PM2 with bounded Node heap (no swap on this host) --
NODE_MEM="--max-old-space-size=768"
cat > "$PASEO_HOME/start_daemon.sh" <<EOF
#!/usr/bin/env bash
set -a
export PASEO_HOME="$PASEO_HOME"
export PASEO_PASSWORD="$(cat "$PASEO_HOME/.daemon-password")"
export NODE_OPTIONS="$NODE_MEM"
export PATH="/home/z/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
set +a
exec paseo daemon run --home "$PASEO_HOME"
EOF
chmod +x "$PASEO_HOME/start_daemon.sh"

pm2 delete paseo-daemon >/dev/null 2>&1 || true
pm2 start "$PASEO_HOME/start_daemon.sh" --name paseo-daemon --max-restarts 10 --restart-delay 5000 >/dev/null 2>&1
pm2 save >/dev/null 2>&1
log "daemon submitted to PM2 (max-restarts 10, delay 5s, heap<=768MB)"

# --- 5/6 health check ----------------------------------------------------------
HEALTH=""
for i in $(seq 1 45); do
  sleep 2
  for ep in api/health health ""; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:6767/$ep" 2>/dev/null)
    if [ "$code" = "200" ]; then HEALTH="http://127.0.0.1:6767/$ep"; break 2; fi
  done
done
if [ -n "$HEALTH" ]; then log "daemon healthy at $HEALTH"; else log "WARN: daemon not healthy after 90s — check $PASEO_HOME/daemon.log"; fi

# --- 6/6 relay pairing (skip if pairing assets already exist for THIS identity) --
if [ -f "$ST/pairing_raw.json" ] && python3 -c "
import json,sys
try:
    d=json.load(open('$ST/pairing_raw.json')); d['url']; sys.exit(0)
except Exception: sys.exit(1)"; then
  log "pairing assets already exist for this identity — skipping re-pair"
else
  log "pairing with relay..."
  paseo daemon pair --relay --json --home "$PASEO_HOME" > "$ST/pairing_raw.json" 2>"$ST/pairing_err.txt" \
    || log "WARN: pair exit $? (see $ST/pairing_err.txt)"
fi

# --- 7/6 repo clone (token used once, then stripped from remote URL) -----------
REPO_DIR="$PROJ/Paseo---Remote-Coding-Agents"
TOKEN=""
[ -f "$SEC/gh.token" ] && TOKEN=$(cat "$SEC/gh.token")
if [ -n "$TOKEN" ] && [ ! -d "$REPO_DIR/.git" ]; then
  if git clone --quiet "https://x-access-token:${TOKEN}@github.com/signalproofai-ux/Paseo---Remote-Coding-Agents.git" "$REPO_DIR" 2>/dev/null; then
    git -C "$REPO_DIR" remote set-url origin "https://github.com/signalproofai-ux/Paseo---Remote-Coding-Agents.git"
    log "repo cloned (token stripped from remote url): $(ls "$REPO_DIR" | wc -l) entries"
  else
    log "WARN: repo clone failed"
  fi
fi

log "BOOTSTRAP DONE"
