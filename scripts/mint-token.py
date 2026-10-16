#!/usr/bin/env python3
"""Mint a local access token for the MCP server (token mode).

  python3 scripts/mint-token.py            # prints a token valid 90 days (use --days N)
  python3 scripts/mint-token.py --check    # mints one and verifies the running server accepts it (exit 1 if not)

Needs MCP_JWT_KEY in .env (scripts/setup.py generates it). Rotating MCP_JWT_KEY revokes every token.
Treat the token like a password: whoever holds it can use every connected Google account.
"""
import argparse
import sys

import kit

p = argparse.ArgumentParser()
p.add_argument("--days", type=int, default=90)
p.add_argument("--env", help="path to the .env file (default: repository .env)")
p.add_argument("--check", action="store_true")
args = p.parse_args()

env = kit.read_env(args.env)
if not env.get("MCP_JWT_KEY"):
    sys.exit("MCP_JWT_KEY is not set in .env: run scripts/setup.py first")
url = kit.canonical_base(kit.public_url(env))
token = kit.mint(env["MCP_JWT_KEY"], url, args.days)

if not args.check:
    print(token)
    sys.exit(0)
try:
    res = kit.rpc(url, token, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                              "clientInfo": {"name": "kit-check", "version": "0"}})
    print("ok: the server accepted the minted token (" + res["result"]["serverInfo"]["name"] + ")")
except Exception as e:  # noqa: BLE001 - any failure means token mode is broken
    sys.exit(f"FAILED: the server did not accept the minted token at {url}: {e}")
