#!/usr/bin/env python3
"""Redacted viewer for the credentials PDF text. Masks secrets, prints structure."""
import re, sys, os

SRC = "/home/z/my-project/secure/extract/raw.txt"
FULL = "/home/z/my-project/secure/creds-full.txt"

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# keep the full version for scripts only (never printed)
os.makedirs(os.path.dirname(FULL), exist_ok=True)
with open(FULL, "w", encoding="utf-8") as f:
    f.write(text)
os.chmod(FULL, 0o600)

SENSITIVE_KEY = re.compile(
    r"(pass(word|wort)?|pwd|token|secret|api[-_ ]?key|access[-_ ]?key|private[-_ ]?key|"
    r"auth|2fa|otp|recovery|licen[cs]e|credential|ssh[-_ ]?key|fingerprint)",
    re.I,
)

TOKENISH = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_\-]{20,}|xox[bap]-[A-Za-z0-9\-]{10,}|"
    r"\b[A-Za-z0-9_\-]{24,}\b)"
)

def mask_value(v: str) -> str:
    v = v.strip()
    if not v:
        return v
    return f"[REDACTED len={len(v)}]"

def mask_email(e: str) -> str:
    m = re.match(r"^(.{1,2}).*?@(.+)$", e)
    if m:
        return f"{m.group(1)}***@{m.group(2)}"
    return "[EMAIL]"

out_lines = []
for line in text.splitlines():
    l = line
    # key: value / key = value / key - value patterns
    def repl_kv(m):
        key, sep, val = m.group(1), m.group(2), m.group(3)
        return f"{key}{sep}{mask_value(val)}"
    l = re.sub(r"([A-Za-z][A-Za-z0-9 _\-/()]{0,40}?)(\s*[:=]\s*)(\S.*)", repl_kv, l, count=1) \
        if SENSITIVE_KEY.search(l.split(":")[0] + l.split("=")[0]) else l
    # generic token-like strings
    l = TOKENISH.sub(lambda m: "[REDACTED len=%d]" % len(m.group(0)), l)
    # emails -> partially masked
    l = re.sub(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", lambda m: mask_email(m.group(0)), l)
    # URLs with embedded creds
    l = re.sub(r"(https?://)([^/\s:@]+):([^@\s]+)@", r"\1\2:[REDACTED]@", l)
    out_lines.append(l)

print("\n".join(out_lines))
print("\n--- structure summary ---")
n_lines = len(text.splitlines())
print(f"total lines: {n_lines}")
