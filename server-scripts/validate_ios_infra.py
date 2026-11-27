#!/usr/bin/env python3
"""Validate ios-build-infra artifacts: YAML parse + ledger dry-run + workflow checks."""
import yaml, json, subprocess, shutil, os

BASE = "/home/z/my-project/download/ios-build-infra"

# 1) YAML validity
for f in [".github/workflows/ios-build.yml", "codemagic.yaml", "DemoApp/project.yml"]:
    d = yaml.safe_load(open(os.path.join(BASE, f)))
    print(f"{f} -> YAML OK, top keys: {list(d.keys())[:6]}")

# 2) workflow-specific checks
wf = yaml.safe_load(open(os.path.join(BASE, ".github/workflows/ios-build.yml")))
on = wf[True] if True in wf else wf.get("on", {})
print("triggers:", list(on.keys()))
assert "workflow_dispatch" in on, "manual dispatch missing"
assert "push" not in on, "push trigger present - violates zero-waste rule"
print("concurrency:", wf["concurrency"])
print("runner:", wf["jobs"]["build"]["runs-on"])
steps = [s["name"] for s in wf["jobs"]["build"]["steps"]]
print("steps:", len(steps))
for s in steps:
    print("   -", s)

# 3) codemagic checks
cm = yaml.safe_load(open(os.path.join(BASE, "codemagic.yaml")))
ios = cm["workflows"]["ios-build"]
print("codemagic: instance =", ios["instance_type"], "| trigger keys =", list(ios.keys()))
assert ios["instance_type"] == "mac_mini_m2"
assert "triggering" not in ios, "triggering events would enable automatic builds"

# 4) ledger dry-run (exact snippet from the workflow)
LEDGER_PY = """import json, sys, os
clock, quota = int(sys.argv[1]), int(sys.argv[2])
try:
    d = json.load(open("build-ledger.json"))
except Exception:
    d = {"quota_minutes_total": 0, "clock_minutes_total": 0, "runs": []}
d["quota_minutes_total"] = d.get("quota_minutes_total", 0) + quota
d["clock_minutes_total"] = d.get("clock_minutes_total", 0) + clock
d.setdefault("runs", []).append({"run_id": os.environ.get("GITHUB_RUN_ID", "local"), "clock_minutes": clock, "quota_minutes": quota})
json.dump(d, open("build-ledger.json", "w"), indent=2)
print(d["quota_minutes_total"])"""
os.makedirs("/tmp/ledgtest", exist_ok=True)
json.dump({"quota_minutes_total": 0, "clock_minutes_total": 0, "runs": []}, open("/tmp/ledgtest/build-ledger.json", "w"))
r = subprocess.run(["python3", "-c", LEDGER_PY, "12", "120"], capture_output=True, text=True, cwd="/tmp/ledgtest")
print("ledger dry-run ->", r.stdout.strip() or r.stderr[:200])
d = json.load(open("/tmp/ledgtest/build-ledger.json"))
print("ledger after: quota total =", d["quota_minutes_total"], "| runs =", len(d["runs"]))

# 5) no secrets committed anywhere in the bundle
import re
bad = []
for root, _, files in os.walk(BASE):
    for f in files:
        p = os.path.join(root, f)
        if p.endswith((".yml", ".md", ".json", ".swift")):
            txt = open(p, errors="replace").read()
            if re.search(r"github_pat_[A-Za-z0-9_]{20,}", txt):
                bad.append(p)
print("secret scan:", "CLEAN" if not bad else f"LEAKED: {bad}")
