#!/usr/bin/env bash
# =============================================================================
# add_gemini_key.sh — wire a Google Gemini API key into OpenCode + the Paseo
# daemon. Usage: bash add_gemini_key.sh AIza...
# - validates the key format
# - verifies it against the Google AI API (lists models)
# - stores it in /home/z/.paseo/server.env (mode 600) as GEMINI_API_KEY
#   and exports it for the opencode CLI test
# - restarts the paseo daemon so the app picks it up
# - runs a REAL opencode call to prove the model answers
# The key is NEVER printed in full (masked output only).
# =============================================================================
set -uo pipefail
export PATH="/home/z/.npm-global/bin:/home/z/.local/bin:$PATH"

KEY="${1:-}"
ENV_FILE="/home/z/.paseo/server.env"

if [ -z "$KEY" ]; then
  echo "ERROR: no key given. Usage: bash add_gemini_key.sh AIza..."
  exit 1
fi
if ! echo "$KEY" | grep -qE '^AIza[0-9A-Za-z_-]{30,}$'; then
  echo "ERROR: key does not look like a Google API key (expected AIza...)."
  exit 1
fi
MASKED="$(echo "$KEY" | cut -c1-6)....$(echo "$KEY" | tail -c 5)"

echo "== 1/4 verifying key against Google AI API =="
CODE=$(curl -s -o /tmp/gemini_models.json -w "%{http_code}" --max-time 15 \
  -H "x-goog-api-key: $KEY" https://generativelanguage.googleapis.com/v1beta/models)
if [ "$CODE" != "200" ]; then
  echo "FAILED: Google rejected the key (HTTP $CODE). No changes made."
  exit 1
fi
MODEL=$(python3 -I -c "
import json
d = json.load(open('/tmp/gemini_models.json'))
names = [m['name'].split('/')[-1] for m in d.get('models', [])]
pref = [n for n in names if 'flash' in n and 'lite' not in n and 'thinking' not in n and 'image' not in n and 'tts' not in n and 'live' not in n]
print(pref[0] if pref else (names[0] if names else ''))
")
if [ -z "$MODEL" ]; then echo "FAILED: no usable model found in response."; exit 1; fi
echo "OK: key valid — will test with model: $MODEL"

echo "== 2/4 storing key in $ENV_FILE (mode 600) =="
touch "$ENV_FILE" && chmod 600 "$ENV_FILE"
if grep -q '^GEMINI_API_KEY=' "$ENV_FILE"; then
  sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$KEY|" "$ENV_FILE"
else
  echo "GEMINI_API_KEY=$KEY" >> "$ENV_FILE"
fi

echo "== 3/4 restarting paseo daemon =="
pm2 restart paseo-daemon >/dev/null 2>&1 && sleep 6
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:6767/api/health)
echo "daemon health after restart: $HEALTH"

echo "== 4/4 real test through opencode ($MODEL) =="
cd /home/z/my-project/projects/demo-web || exit 1
OUT=$(GEMINI_API_KEY="$KEY" timeout 90 opencode run --model "google/$MODEL" "Reply with exactly: GEMINI-OK" 2>&1 | tail -3)
echo "$OUT"
if echo "$OUT" | grep -q "GEMINI-OK"; then
  echo "SUCCESS: Gemini is wired in (key $MASKED, model google/$MODEL)."
  exit 0
else
  echo "WARN: API accepted the key but the agent test did not return GEMINI-OK — check output above."
  exit 2
fi
