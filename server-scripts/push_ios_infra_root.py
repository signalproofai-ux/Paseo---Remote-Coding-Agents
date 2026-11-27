#!/usr/bin/env python3
"""Push the iOS build workflow + DemoApp to the Paseo repo ROOT so GitHub
Actions recognizes the workflow, then (if possible) dispatch a verification
build. Additive only: every target path is checked to be absent first.
Secrets: token read from secure/gh.token, never printed."""
import base64, json, os, sys, urllib.request

TOKEN = open("/home/z/my-project/secure/gh.token").read().strip()
REPO = "signalproofai-ux/Paseo---Remote-Coding-Agents"
API = f"https://api.github.com/repos/{REPO}"
BUNDLE = "/home/z/my-project/download/ios-build-infra"

def api(method, path, payload=None):
    req = urllib.request.Request(API + path, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "infra-setup",
    })
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as r:
            return r.status, json.load(r) if r.status != 204 else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return e.code, {"message": body}

# 1) verify targets are absent at root (additive-only rule)
st, tree = api("GET", "/git/trees/main?recursive=1")
paths = {t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"}
targets = [
    ".github/workflows/ios-build.yml",
    "project.yml",
    "Sources/DemoAppApp.swift",
    "Sources/ContentView.swift",
    "build-ledger.json",
]
existing = [t for t in targets if t in paths]
print("already existing at root:", existing or "none — all additive OK")

# 2) commit each file via contents API (main branch, direct commit)
files = {
    ".github/workflows/ios-build.yml": f"{BUNDLE}/.github/workflows/ios-build.yml",
    "project.yml": f"{BUNDLE}/DemoApp/project.yml",
    "Sources/DemoAppApp.swift": f"{BUNDLE}/DemoApp/Sources/DemoAppApp.swift",
    "Sources/ContentView.swift": f"{BUNDLE}/DemoApp/Sources/ContentView.swift",
    "build-ledger.json": f"{BUNDLE}/build-ledger.json",
}
committed = []
for path, local in files.items():
    if path in existing:
        print(f"SKIP existing: {path}")
        continue
    content = base64.b64encode(open(local, "rb").read()).decode()
    st, resp = api("PUT", f"/contents/{path}", {
        "message": f"ci: add {path} (iOS build infra, additive)",
        "content": content,
        "branch": "main",
    })
    print(f"PUT {path}: HTTP {st} {'' if st in (200,201) else resp.get('message','')}")
    if st in (200, 201):
        committed.append(path)

# 3) dispatch a manual verification build (needs Actions: write)
if ".github/workflows/ios-build.yml" in committed or ".github/workflows/ios-build.yml" in paths:
    st, resp = api("POST", "/actions/workflows/ios-build.yml/dispatches", {
        "ref": "main",
        "inputs": {"configuration": "Release", "run_tests": "false", "signing": "auto",
                    "export_method": "ad-hoc", "scheme": ""},
    })
    print(f"dispatch: HTTP {st} {'' if st == 204 else resp.get('message','')[:200]}")
else:
    print("dispatch skipped: workflow file not present at root")
