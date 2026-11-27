#!/usr/bin/env python3
# finalize_paseo_files.py — build fresh pairing deliverables in download/
import base64
import json
import os
import shutil

DL = "/home/z/my-project/download"
RAW = "/home/z/my-project/scripts/pairing_raw.json"
PW_FILE = "/home/z/.paseo/.daemon-password"

os.makedirs(DL, exist_ok=True)
d = json.load(open(RAW))
url = d["url"]
uri = d.get("connectionUri", "")

# decode offer to show serverId in the card
offer_b64 = url.split("#offer=")[1]
offer = json.loads(base64.b64decode(offer_b64 + "=" * (-len(offer_b64) % 4)))
server_id = offer.get("serverId", "?")

# 1) pairing link file (same format as the previous one)
with open(f"{DL}/paseo-pairing-link.txt", "w") as f:
    f.write(
        "PASEO PAIRING LINK (NEW — the old server identity died with the sandbox reset.\n"
        "Scan the QR in paseo-pairing-qr.png with the Paseo iOS app,\n"
        "or open this URL on the iPhone):\n\n"
        f"{url}\n\n"
        'Alternative connection URI (use the app\'s "Paste pairing link" option):\n\n'
        f"{uri}\n"
    )

# 2) QR png
import qrcode
img = qrcode.make(url)
img.save(f"{DL}/paseo-pairing-qr.png")

# 3) daemon password copy
if os.path.exists(PW_FILE):
    shutil.copyfile(PW_FILE, f"{DL}/daemon-password.txt")
    os.chmod(f"{DL}/daemon-password.txt", 0o600)

# 4) connection card
card = f"""================================================================
 PASEO CONNECTION CARD  (RESTORED {server_id}) — 2026-11-27
================================================================

WHAT HAPPENED
  The chat sandbox was reset between sessions, so the previous
  daemon and its keypair were wiped. The old QR/link can never
  reconnect. A fresh daemon is now RUNNING with a new identity,
  and it is already connected to the encrypted relay.

SERVER STATUS (verified live)
  daemon        : paseo 0.17.6 on 127.0.0.1:6767 (PM2: online)
  relay         : relay.paseo.sh:443 — relay_control_connected
  agents        : opencode 1.19.6 (FREE built-in model, no key)
                  claude 2.1.332 (needs your Anthropic login)
  identity      : {server_id}

CONNECT YOUR IPHONE (~1 minute)
  1. Paseo app -> Settings -> Add host -> Scan QR code
     -> scan: paseo-pairing-qr.png
  2. Or: "Paste pairing link" -> paseo-pairing-link.txt
  3. If asked for the daemon password -> daemon-password.txt
  (The old host entry in the app will stay offline — you can
   delete it; add the new one with the QR above.)

PROJECTS ON THE SERVER
  /home/z/my-project/projects/Paseo---Remote-Coding-Agents  (your GitHub repo)
  /home/z/my-project/projects/demo-web                      (sandbox demo)
  In the app: Add a project -> /home/z/my-project

NOTES
  - Un-pushed work from the old phone session was lost with the
    old sandbox; ask the agent to rebuild — it is fast.
  - The GitHub token you pasted in chat still works; rotate it soon.
================================================================
"""
with open(f"{DL}/CONNECTION-CARD.txt", "w") as f:
    f.write(card)

# 5) re-serve the static documents from upload so their links work again
for name, dst in [
    ("Paseo_Cloud_Deployment_Report.docx", "Paseo_Cloud_Deployment_Report.docx"),
    ("Paseo_Cloud_Deployment_Report.pdf", "Paseo_Cloud_Deployment_Report.pdf"),
    ("provision-paseo-server.sh", "provision-paseo-server.sh"),
    ("ios-ipa-build.yml.txt", "ios-ipa-build.yml"),
]:
    src = f"/home/z/my-project/upload/{name}"
    if os.path.exists(src):
        shutil.copyfile(src, f"{DL}/{dst}")

print("serverId:", server_id)
print("files:", sorted(os.listdir(DL)))
