#!/usr/bin/env python3
"""Stage GitHub token from creds-full.txt into secure/gh.token (0600) without printing it."""
import re, os

with open("/home/z/my-project/secure/creds-full.txt") as f:
    lines = [l.rstrip("\n") for l in f]

# find line starting with 'Token' then collect following base62 lines
tok = ""
collecting = False
for l in lines:
    s = l.strip()
    if s.lower().startswith("token"):
        collecting = True
        rest = s.split("=", 1)[1].strip() if "=" in s else ""
        tok += rest
        continue
    if collecting:
        if re.fullmatch(r"[A-Za-z0-9_]{8,}", s):
            tok += s
        else:
            break

tok = tok.strip()
if not tok.startswith("github_pat_") and not tok.startswith(("ghp_", "gho_")):
    # maybe the token itself was on the same line as other text; search whole text
    m = re.search(r"github_pat_[A-Za-z0-9_]{60,}", "\n".join(lines))
    tok = m.group(0) if m else tok

p = "/home/z/my-project/secure/gh.token"
with open(p, "w") as f:
    f.write(tok)
os.chmod(p, 0o600)
print(f"token staged: prefix={tok[:11]}... len={len(tok)} valid_format={'yes' if tok.startswith('github_pat_') else 'NO'}")
