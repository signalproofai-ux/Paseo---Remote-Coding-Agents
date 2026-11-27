#!/usr/bin/env bash
# =============================================================================
# persist_backup.sh — auto-backup of the workspace to the user's private GitHub
# repo. Runs in a PM2 loop (persist-sync). Never prints the token.
# Pushes: projects/* (code), server scripts. Excludes: secrets, junk, zips.
# =============================================================================
set -uo pipefail
export PATH="/home/z/.npm-global/bin:/home/z/.local/bin:$PATH"
WS="/home/z/my-project"
REPO_DIR="$WS/projects/Paseo---Remote-Coding-Agents"
LOG="$WS/scripts/persist_status.log"
STAMP="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"

[ -d "$REPO_DIR/.git" ] || { echo "$STAMP ERROR: clone missing" >> "$LOG"; exit 1; }

# 1) mirror every project dir (except the clone itself) into the repo
shopt -s nullglob
for d in "$WS"/projects/*/; do
  name="$(basename "$d")"
  [ "$name" = "Paseo---Remote-Coding-Agents" ] && continue
  rsync -a --delete \
    --exclude node_modules --exclude .git --exclude __pycache__ \
    --exclude .venv --exclude venv --exclude '*.pyc' --exclude .next \
    "$d" "$REPO_DIR/$name/"
done

# 2) server scripts (useful for restore; no secrets inside)
mkdir -p "$REPO_DIR/server-scripts"
cp -f "$WS"/scripts/*.sh "$WS"/scripts/*.py "$REPO_DIR/server-scripts/" 2>/dev/null || true

# 3) make sure secrets never enter the repo
cat > "$REPO_DIR/.gitignore" <<'EOF'
.env
*.token
.gh-token
upload/
node_modules/
__pycache__/
*.pyc
.venv/
.next/
download/*.zip
EOF

cd "$REPO_DIR" || exit 1
git config user.name "signalproofai-ux" 2>/dev/null
git config user.email "signalproofai-ux@users.noreply.github.com" 2>/dev/null
git add -A
if git diff --cached --quiet; then
  echo "$STAMP no changes" >> "$LOG"
  exit 0
fi
git commit -q -m "auto-backup: workspace snapshot $STAMP" || { echo "$STAMP commit failed" >> "$LOG"; exit 1; }

# 4) push with the token from the chat export (never printed, never stored in config)
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
if [ -z "$TOKEN" ]; then echo "$STAMP ERROR: no token" >> "$LOG"; exit 1; fi
if git push -q --force "https://x-access-token:${TOKEN}@github.com/signalproofai-ux/Paseo---Remote-Coding-Agents.git" main 2>>"$LOG"; then
  echo "$STAMP pushed: $(git rev-parse --short HEAD) files=$(git show --stat --format= HEAD | tail -1 | head -c 60)" >> "$LOG"
else
  echo "$STAMP push FAILED" >> "$LOG"
  exit 1
fi
