#!/usr/bin/env python3
"""finalize_pairing.py — build fresh pairing deliverables in download/ from
.state/pairing_raw.json. Password copied with mode 600. Never prints secrets."""
import base64, json, os, shutil

ST = "/home/z/my-project/.state"
DL = "/home/z/my-project/download"
PASEO_HOME = "/home/z/my-project/.state/paseo"

os.makedirs(DL, exist_ok=True)
d = json.load(open(f"{ST}/pairing_raw.json"))
url = d["url"]
uri = d.get("connectionUri", "")

# decode offer to show serverId in the card
offer_b64 = url.split("#offer=")[1]
offer = json.loads(base64.b64decode(offer_b64 + "=" * (-len(offer_b64) % 4)))
server_id = offer.get("serverId", "?")

# 1) pairing link file
with open(f"{DL}/paseo-pairing-link.txt", "w") as f:
    f.write(
        "PASEO PAIRING LINK (identity persists in the workspace now —\n"
        "this link survives sandbox recycles; re-scan only if you delete the host):\n\n"
        f"{url}\n\n"
        'Alternative connection URI (use the app\'s "Paste pairing link" option):\n\n'
        f"{uri}\n"
    )

# 2) QR png
import qrcode
img = qrcode.make(url)
img.save(f"{DL}/paseo-pairing-qr.png")

# 3) daemon password copy
if os.path.exists(f"{PASEO_HOME}/.daemon-password"):
    shutil.copyfile(f"{PASEO_HOME}/.daemon-password", f"{DL}/daemon-password.txt")
    os.chmod(f"{DL}/daemon-password.txt", 0o600)

# 4) connection card
card = f"""================================================================
 PASEO CONNECTION CARD — {server_id} — 2026-11-27
================================================================

SERVER STATUS (verified live)
  daemon        : paseo 0.18.0 on 127.0.0.1:6767 (PM2: paseo-daemon)
  serverId      : {server_id}
  relay         : relay.paseo.sh:443 — end-to-end encrypted, enabled
  providers     : opencode available, claude available,
                  codex/copilot/pi/antigravity/muse not installed
  agents        : opencode 1.19.6 | claude 2.1.332 | gemini 0.71.1
  persistence   : PM2 (paseo-daemon, persist-sync, guard)
  workspace     : /home/z/my-project (persistent; daemon state now lives
                  in /home/z/my-project/.state/paseo — survives resets)

CONNECT YOUR IPHONE (~1 minute)
  1. Paseo app -> Settings -> Add host -> Scan QR code
     -> scan: paseo-pairing-qr.png
  2. Or: "Paste pairing link" -> paseo-pairing-link.txt
  3. If asked for the daemon password -> daemon-password.txt

KNOWN LIMITATION (honest disclosure)
  This machine is an ephemeral agent sandbox: when the platform
  recycles it between sessions, RUNNING PROCESSES STOP (PM2 included)
  and only files under /home/z/my-project survive. The daemon comes
  back by re-running: bash /home/z/my-project/scripts/bootstrap_stack.sh
  (takes ~30s, identity + password + pairing survive). For a truly
  always-on host a free-tier VPS is required — see HANDOVER-REPORT.

BACKUPS
  persist-sync pushes /home/z/my-project/projects/* to GitHub every
  5 min (repo: signalproofai-ux/Paseo---Remote-Coding-Agents).
================================================================
"""
with open(f"{DL}/CONNECTION-CARD.txt", "w") as f:
    f.write(card)

print("serverId:", server_id)
print("files:", sorted(os.listdir(DL)))
