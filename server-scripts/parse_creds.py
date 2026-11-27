#!/usr/bin/env python3
"""Parse the creds PDF text: list key names (values masked), find URLs/domains,
decode any embedded base64 image and any QR code inside it. Secrets never printed."""
import re, base64, os, sys

SRC = "/home/z/my-project/secure/creds-full.txt"
SEC = "/home/z/my-project/secure"

with open(SRC) as f:
    text = f.read()

lines = [l.rstrip("\n") for l in text.splitlines()]
print("== raw line map (chars masked, first token shown) ==")
for i, l in enumerate(lines):
    s = l.strip()
    if not s:
        print(f"{i:02d}: <empty>")
        continue
    # classify
    if s.startswith("http"):
        m = re.match(r"(https?://)([^/]+)(/.*)?", s)
        print(f"{i:02d}: URL -> scheme={m.group(1)} host={m.group(2)} path_len={len(m.group(3) or '')}")
    elif "=" in s and not s.lower().startswith(("data:", "png")):
        k = s.split("=", 1)[0].strip()
        v = s.split("=", 1)[1].strip() if "=" in s else ""
        print(f"{i:02d}: KEY '{k}' value_len={len(v)} value_preview={'<base64/img>' if len(v)>40 else '[REDACTED]'}")
    elif s.lower().startswith(("png", "data:", "base64")) or re.fullmatch(r"[A-Za-z0-9+/=]{20,}", s):
        print(f"{i:02d}: BASE64/IMG chunk len={len(s)}")
    else:
        # show only structure: mask everything except pure alphabetic words < 12 chars
        words = re.findall(r"[A-Za-z]{3,12}", s)
        print(f"{i:02d}: TEXT len={len(s)} words={words[:12]}")

# key=value continuation: find real pairs by joining lines
joined = text
print("\n== domains mentioned ==")
doms = set(re.findall(r"\b(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24}\b", joined.lower()))
for d in sorted(doms):
    print("  ", d)

print("\n== emails mentioned ==")
for e in set(re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", joined)):
    m = re.match(r"^(.{1,2}).*?@(.+)$", e)
    print("  ", f"{m.group(1)}***@{m.group(2)}" if m else "[EMAIL]")

# extract base64 image(s)
print("\n== embedded images ==")
b64_chunks = []
buf = []
for l in lines:
    s = l.strip()
    if re.fullmatch(r"[A-Za-z0-9+/=\s]{20,}", s) or "base64," in s.lower():
        buf.append(s)
    else:
        if buf:
            b64_chunks.append("".join(buf)); buf = []
if buf:
    b64_chunks.append("".join(buf))
idx = 0
for chunk in b64_chunks:
    chunk = re.sub(r"^[A-Za-z]+;base64,", "", chunk)
    chunk = re.sub(r"\s+", "", chunk)
    if len(chunk) < 100:
        continue
    try:
        data = base64.b64decode(chunk, validate=False)
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            idx += 1
            p = f"{SEC}/embedded_{idx}.png"
            with open(p, "wb") as f:
                f.write(data)
            os.chmod(p, 0o600)
            print(f"   saved PNG #{idx} bytes={len(data)} -> {p}")
    except Exception as ex:
        print("   decode fail:", type(ex).__name__)
print("\n== QR decode ==")
import cv2
det = cv2.QRCodeDetector()
for i in range(1, idx + 1):
    p = f"{SEC}/embedded_{i}.png"
    img = cv2.imread(p)
    if img is None:
        print(f"   #{i}: unreadable as image")
        continue
    try:
        data, pts, _ = det.detectAndDecode(img)
    except Exception as ex:
        data = ""
    if data:
        kind = "otpauth 2FA setup" if data.startswith("otpauth://") else ("URL" if data.startswith("http") else "text")
        host = ""
        if data.startswith("http"):
            m = re.match(r"https?://([^/]+)", data)
            host = " host=" + m.group(1)
        if data.startswith("otpauth://"):
            m = re.match(r"otpauth://[^/]+/([^?]+)", data)
            lbl = m.group(1) if m else ""
            print(f"   #{i}: QR={kind} label={lbl} secret_saved=yes(len={len(data)})")
            with open(f"{SEC}/qr_content_{i}.txt", "w") as f:
                f.write(data)
            os.chmod(f"{SEC}/qr_content_{i}.txt", 0o600)
        else:
            print(f"   #{i}: QR={kind}{host} len={len(data)}")
            with open(f"{SEC}/qr_content_{i}.txt", "w") as f:
                f.write(data)
            os.chmod(f"{SEC}/qr_content_{i}.txt", 0o600)
    else:
        print(f"   #{i}: no QR detected")
