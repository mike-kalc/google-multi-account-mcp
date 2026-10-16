"""Shared helpers for scripts/setup.py and scripts/mint-token.py (standard library only)."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "http://localhost:4243"


def read_env(path=None):
    values = {}
    for line in Path(path or ROOT / ".env").read_text().splitlines():
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2).strip()
    return values


def write_env(updates, path=None):
    """Set KEY=value lines in .env (append when missing). Atomic, keeps the file mode."""
    path = Path(path or ROOT / ".env")
    text = path.read_text()
    for key, value in updates.items():
        text, n = re.subn(rf"(?m)^{re.escape(key)}=.*$", lambda m: f"{key}={value}", text, count=1)
        if n == 0:
            text = text.rstrip("\n") + f"\n{key}={value}\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".env.")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(tmp, path.stat().st_mode & 0o777)
    os.replace(tmp, path)


def public_url(env):
    return (env.get("MCP_PUBLIC_URL") or DEFAULT_URL).rstrip("/")


def canonical_base(url):
    """The server signs and checks tokens against the publicUrl it reports on /health."""
    try:
        with urllib.request.urlopen(url + "/health", timeout=5) as r:
            return json.load(r)["publicUrl"].rstrip("/")
    except Exception:
        return url


def new_jwt_key():
    return base64.b64encode(secrets.token_bytes(32)).decode()


def _secret(key):
    # mirrors upstream deriveKey (marked compat-frozen): a base64 key of 32 bytes is used as is, anything else is sha256'd
    raw = base64.b64decode(key + "=" * (-len(key) % 4))
    return raw if len(raw) == 32 else hashlib.sha256(key.encode()).digest()


def mint(key, base, days=90):
    """HS256 access token the server accepts on /mcp (claims as in upstream src/mcp-token.ts)."""
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    now = int(time.time())
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps({"scope": "mcp:use", "purpose": "mcp_access", "iss": base, "sub": "owner",
                           "aud": base + "/mcp", "iat": now, "exp": now + days * 86400,
                           "jti": secrets.token_urlsafe(16)}, separators=(",", ":")).encode())
    sig = b64(hmac.new(_secret(key), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def rpc(url, token, method, params=None, id=1):
    req = urllib.request.Request(
        url + "/mcp",
        json.dumps({"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}).encode(),
        {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
         "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
    if "data:" in body:  # server-sent-events framing
        body = [l[5:].strip() for l in body.splitlines() if l.startswith("data:")][-1]
    return json.loads(body)


_initialized = set()


def call_tool(url, token, name, args=None):
    # The server remembers the client's capabilities per token from `initialize`. Without it, tools that may
    # ask the client for input (account_reauth) wait for an answer that never comes, so always initialize first.
    if token not in _initialized:
        rpc(url, token, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                       "clientInfo": {"name": "kit-scripts", "version": "0"}})
        _initialized.add(token)
    res = rpc(url, token, "tools/call", {"name": name, "arguments": args or {}})["result"]
    return res["content"][0]["text"], bool(res.get("isError"))
