#!/usr/bin/env python3
"""Write one value from stdin into .env without echoing it (keeps secrets out of chat and shell history).

  macOS:   pbpaste | python3 scripts/set-env.py GOOGLE_CLIENT_SECRET 'GOCSPX-[A-Za-z0-9_-]{20,}'
  Linux:   wl-paste | python3 scripts/set-env.py ...     (or: xclip -o -selection clipboard | ...)
  Windows: Get-Clipboard | python scripts/set-env.py ...  (PowerShell; or run everything inside WSL)

Client ID regex: '[0-9]+-[a-z0-9]+\\.apps\\.googleusercontent\\.com'
The value must match the regex fully, otherwise nothing is written. The key must appear exactly once in .env.
The file is replaced atomically and keeps its permissions.
"""
import os
import re
import sys
import tempfile

key, pattern = sys.argv[1], sys.argv[2]
value = sys.stdin.read().strip()
if not re.fullmatch(pattern, value):
    sys.exit(f"unexpected format for {key} (len={len(value)}), nothing written")
with open(".env") as f:
    text = f.read()
text, n = re.subn(rf"(?m)^{re.escape(key)}=.*$", lambda m: f"{key}={value}", text)
if n != 1:
    sys.exit(f"{key} must appear exactly once in .env (found {n})")
mode = os.stat(".env").st_mode & 0o777
fd, tmp = tempfile.mkstemp(dir=".", prefix=".env.")
with os.fdopen(fd, "w") as f:
    f.write(text)
os.chmod(tmp, mode)
os.replace(tmp, ".env")
print(f"{key} written to .env (length {len(value)})")
