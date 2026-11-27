#!/usr/bin/env python3
"""Print the GitHub URL from the doc (path only if clean) + repo inventory via token."""
import re, json, subprocess, os

# 1) URL from doc
with open("/home/z/my-project/secure/creds-full.txt") as f:
    first = f.readline().strip()
m = re.match(r"(https?://)([^/]+)(/.*)", first)
if m and "token" not in first.lower() and not re.search(r"[A-Za-z0-9_]{30,}@", first):
    print("doc URL:", m.group(1) + m.group(2) + m.group(3))
else:
    print("doc URL: (contains credential-like segment; host=%s)" % (m.group(2) if m else "?"))

# 2) repos
tok = open("/home/z/my-project/secure/gh.token").read().strip()
env = dict(os.environ, GH=tok)
cmd = 'curl -sS -H "Authorization: Bearer $GH" -H "Accept: application/vnd.github+json" "https://api.github.com/user/repos?per_page=100&sort=updated"'
out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=env)
repos = json.loads(out.stdout)
if isinstance(repos, dict):
    print("API error:", repos.get("message"))
else:
    print(f"\nrepos accessible: {len(repos)}")
    for r in repos:
        perms = r.get("permissions") or {}
        print(f"  - {r['full_name']}  private={r['private']} size={r['size']}KB default={r.get('default_branch')} push={perms.get('push')} updated={r['updated_at']}")
