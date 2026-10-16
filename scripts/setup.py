#!/usr/bin/env python3
"""Guided setup for google-multi-account-mcp (standard library only).

  python3 scripts/setup.py                  # first run: .env -> server -> register clients -> authorize accounts
  python3 scripts/setup.py add-account      # add another Google account later (no file editing, no restart)

Options: --skip-clients (do not register Claude Code / Codex), --no-open (print links instead of opening a browser).
Safe to re-run: existing values are kept when you press Enter. Needs Docker with Compose v2 and your OAuth client
(docs/google-cloud-setup.md). Nothing here prints the token or the client secret.
"""
import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import kit

NAME = "google-multi"
VOLUME = "google-multi-account-mcp_mcp-config"
ID_RE = r"[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com"
SECRET_RE = r"GOCSPX-[A-Za-z0-9_-]{20,}"
ALIAS_RE = r"[A-Za-z0-9_-]+"
EMAIL_RE = r"[^\s,:@]+@[^\s,:@]+"
AUTHORIZED = {"ok", "expired_refreshable"}


def ask(prompt, default=""):
    try:
        value = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    except EOFError:
        if default:
            return default
        sys.exit("\ninput closed")
    return value or default


def yes(prompt, default=True):
    try:
        value = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    except EOFError:
        return default
    return default if not value else value.startswith("y")


def ask_valid(prompt, pattern, current, secret=False):
    while True:
        if secret:
            try:
                value = getpass.getpass(f"{prompt}{' [Enter keeps the current one]' if current else ''}: ").strip() or current
            except EOFError:
                value = current or sys.exit("\ninput closed")
        else:
            value = ask(prompt, current)
        if re.fullmatch(pattern, value):
            return value
        print("  unexpected format, try again")


def ask_account():
    alias = ask_valid("  Account alias, a short label you will use to pick it (e.g. work)", ALIAS_RE, "")
    email = ask_valid(f"  Google email of '{alias}' (the account you will sign in with)", EMAIL_RE, "")
    return alias, email


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=kit.ROOT, **kw)


def register_claude(url, token):
    claude = shutil.which("claude")
    if not claude:
        return print("  Claude Code not found, skipped")
    if run([claude, "mcp", "get", NAME], capture_output=True).returncode == 0:
        if not yes(f"  '{NAME}' is already registered in Claude Code. Replace it?", False):
            return
        run([claude, "mcp", "remove", NAME, "-s", "user"], capture_output=True)
    elif not yes("  Register the server in Claude Code (user scope; the token is stored in ~/.claude.json)?"):
        return
    # name and URL before -H: the header option is variadic and would swallow them
    r = run([claude, "mcp", "add", "--transport", "http", "-s", "user", NAME, url + "/mcp",
             "-H", f"Authorization: Bearer {token}"], capture_output=True, text=True)
    print("  Claude Code: " + ("registered" if r.returncode == 0 else "FAILED " + r.stderr.strip()[:200]))


def register_codex(url, token):
    if not shutil.which("codex"):
        return print("  Codex not found, skipped")
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    cfg = home / "config.toml"
    text = cfg.read_text() if cfg.exists() else ""
    if re.search(rf"(?m)^\[mcp_servers\.{re.escape(NAME)}[\].]", text):
        return print(f"  Codex already has '{NAME}' in {cfg}; run `codex mcp remove {NAME}` and re-run to replace it")
    if not yes(f"  Register the server in Codex (appends a section to {cfg}; a backup is kept)?"):
        return
    home.mkdir(parents=True, exist_ok=True)
    if cfg.exists():
        shutil.copy(cfg, cfg.with_name(f"config.toml.bak-{int(time.time())}"))
    with open(cfg, "a") as f:
        f.write(f"\n[mcp_servers.{NAME}]\nurl = {json.dumps(url + '/mcp')}\n"
                f"http_headers = {{ Authorization = {json.dumps('Bearer ' + token)} }}\n")
    try:
        os.chmod(cfg, 0o600)
    except OSError:
        pass
    print("  Codex: registered")


def accounts_info(url, token):
    text, _ = kit.call_tool(url, token, "account_list")
    return [(a["alias"], a["email"], a["tokenStatus"]) for a in json.loads(text)["accounts"]]


def authorize_one(url, token, alias, email, no_open):
    for _ in range(3):
        status = {a: s for a, _e, s in accounts_info(url, token)}.get(alias)
        if status in AUTHORIZED:
            return print(f"  {alias}: authorized")
        text, _err = kit.call_tool(url, token, "account_reauth", {"alias": alias})
        link = re.search(r"https?://\S+", text)
        if not link:
            return print(f"  {alias}: no authorization link returned: {text[:200]}")
        print(f"\n  >>> Authorize '{alias}' with the Google account {email} <<<")
        print("  Pick exactly that account on Google's screen, then Allow (unverified app: Advanced -> Continue).")
        if no_open:
            print(f"  {link.group(0)}")
        else:
            webbrowser.open(link.group(0))
        if ask("  Press Enter when done, or type s to skip", "").lower().startswith("s"):
            return
    print(f"  {alias}: still not authorized; run `python3 scripts/setup.py` again or ask the assistant to call account_reauth")


def add_account(url, token, no_open):
    alias, email = ask_account()
    text, err = kit.call_tool(url, token, "account_add", {"alias": alias, "email": email})
    if err:
        return print(f"  could not add '{alias}': {text[:300]}")
    authorize_one(url, token, alias, email, no_open)


def connect():
    """Returns (url, token) for the running server, minting a local token from MCP_JWT_KEY."""
    env = kit.read_env()
    url = kit.canonical_base(kit.public_url(env))
    token = kit.mint(env["MCP_JWT_KEY"], url)
    try:
        kit.rpc(url, token, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                           "clientInfo": {"name": "kit-setup", "version": "0"}})
    except Exception as e:  # noqa: BLE001
        sys.exit(f"the server did not accept the locally minted token at {url}: {e}")
    return url, token


def compose_up():
    if run(["docker", "compose", "up", "-d", "--wait", "--wait-timeout", "120"]).returncode:
        sys.exit("docker compose failed; see the output above")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", choices=["setup", "add-account"], default="setup")
    ap.add_argument("--skip-clients", action="store_true", help="do not register Claude Code / Codex")
    ap.add_argument("--no-open", action="store_true", help="print authorization links instead of opening a browser")
    args = ap.parse_args()
    os.chdir(kit.ROOT)

    if args.command == "add-account":
        if not (kit.ROOT / ".env").exists() or not kit.read_env().get("MCP_JWT_KEY"):
            sys.exit("run `python3 scripts/setup.py` first")
        url, token = connect()
        return add_account(url, token, args.no_open)

    if not shutil.which("docker") or run(["docker", "compose", "version"], capture_output=True).returncode:
        sys.exit("Docker with Compose v2 is required (see README, Requirements)")
    env_file = kit.ROOT / ".env"
    if not env_file.exists():
        shutil.copy(kit.ROOT / ".env.example", env_file)
        try:
            os.chmod(env_file, 0o600)
        except OSError:
            pass
    env = kit.read_env()

    print("Step 1/4: configuration (Enter keeps the current value)")
    updates = {"GOOGLE_CLIENT_ID": ask_valid("OAuth client ID", ID_RE, env.get("GOOGLE_CLIENT_ID", "")),
               "GOOGLE_CLIENT_SECRET": ask_valid("OAuth client secret (hidden)", SECRET_RE,
                                                 env.get("GOOGLE_CLIENT_SECRET", ""), secret=True)}
    pending = dict(p.split(":", 1) for p in env.get("GOOGLE_ACCOUNTS", "").split(",") if ":" in p)
    fresh = not pending and run(["docker", "volume", "inspect", VOLUME], capture_output=True).returncode != 0
    if fresh:
        print("The server needs one Google account to start (more can be added afterwards without editing files).")
        pending = dict([ask_account()])
    if pending:
        updates["GOOGLE_ACCOUNTS"] = ",".join(f"{a}:{e}" for a, e in pending.items())
        updates["MCP_OWNER_EMAILS"] = ",".join(sorted(set(pending.values())))
    if not env.get("MCP_JWT_KEY"):
        updates["MCP_JWT_KEY"] = kit.new_jwt_key()
    kit.write_env(updates)

    print("\nStep 2/4: starting the server")
    compose_up()
    url, token = connect()
    if pending:  # accounts now live in the server's volume; GOOGLE_ACCOUNTS would block adding more later
        before = sorted(a for a, _e, _s in accounts_info(url, token))
        kit.write_env({"GOOGLE_ACCOUNTS": ""})
        compose_up()
        url, token = connect()
        if sorted(a for a, _e, _s in accounts_info(url, token)) != before:
            kit.write_env({"GOOGLE_ACCOUNTS": updates["GOOGLE_ACCOUNTS"]})
            compose_up()
            url, token = connect()
            print("  note: could not move the accounts into the server; GOOGLE_ACCOUNTS stays in .env")
    print(f"  server up at {url}/mcp, local token accepted")

    print("\nStep 3/4: connect your clients" + (" (skipped)" if args.skip_clients else ""))
    if not args.skip_clients:
        register_claude(url, token)
        register_codex(url, token)

    print("\nStep 4/4: authorize each Google account")
    for alias, email, _status in accounts_info(url, token):
        authorize_one(url, token, alias, email, args.no_open)
    while yes("\nAdd another Google account now?", False):
        add_account(url, token, args.no_open)
    print("\nStatus:", ", ".join(f"{a}={s}" for a, _e, s in accounts_info(url, token)))
    print("Done. The default profile is read-only; see the README before enabling writes.")


if __name__ == "__main__":
    main()
