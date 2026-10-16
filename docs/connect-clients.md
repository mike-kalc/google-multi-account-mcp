# Connect Claude Code or Codex

`python3 scripts/setup.py` does everything below for you (it asks before touching any client config). This page is the manual version.

The server listens on `http://localhost:4243/mcp` (loopback only). Always use the host name `localhost`; `127.0.0.1` is rejected by the server's Host check.

## Token mode (default)

Mint a token from the `MCP_JWT_KEY` in your `.env` (90 days; `--days N` to change). It is printed to the terminal only, so treat it like a password:

```bash
python3 scripts/mint-token.py
python3 scripts/mint-token.py --check      # verifies the running server accepts a freshly minted token
```

**Claude Code** (name and URL before `-H`, which is variadic):

```bash
claude mcp add --transport http -s user google-multi http://localhost:4243/mcp -H "Authorization: Bearer <token>"
```

Already registered under that name? Run `claude mcp remove google-multi -s user` first.

**Codex** (CLI, ChatGPT desktop app, IDE extension share `~/.codex/config.toml`): append

```toml
[mcp_servers.google-multi]
url = "http://localhost:4243/mcp"
http_headers = { Authorization = "Bearer <token>" }
```

Alternatively `codex mcp add google-multi --url http://localhost:4243/mcp --bearer-token-env-var GOOGLE_MULTI_TOKEN`, which needs that variable in the environment of every Codex process. Do not run `codex mcp add` without a bearer variable: it starts an OAuth login that waits for a browser.

To renew or revoke: mint a new token and register again; changing `MCP_JWT_KEY` invalidates every token.

## Authorize each Google account

The setup script does this, or ask the assistant for `account_reauth`. A tool call (or the script) returns a signed link, valid 1 hour. Open it, pick **the Google account of that alias** (a different account is refused with `access_denied`), and press **Allow** (External apps show "unverified app": Advanced -> Continue).

Useful tools: `account_list` (aliases and token status), `account_reauth` (new link for an alias), `account_add` (new alias + Google email, then the same consent).

**What Google shows.** The Google grant belongs to the server's OAuth client, not to Claude Code or Codex: both tools talk to your server, and the server holds one token per account. So each Google account lists **one** entry (your app's name) under [Third-party access](https://myaccount.google.com/connections), whichever and however many AI tools you connect. Removing that entry revokes the server's access to the account for all tools at once, and the account then needs `account_reauth` or `python3 scripts/setup.py`. Every server that uses the same OAuth client shares the entry too.

**If `account_reauth` hangs in a Claude client** (observed with Claude Code 2.1.301 and later): the server waits for an answer to a request that the app does not show, so do not call it again. Run `python3 scripts/setup.py` instead: it authorizes every account that still needs it and does not trigger the wait.

## Smoke test

Ask the assistant to list your Google accounts, then to read-only search one mailbox per alias.

## OAuth mode (optional)

The server also has its own OAuth sign-in with an owner gate (`MCP_OWNER_EMAILS`). Clients that support it can use it instead of a token.

- **Claude Code** refuses sign-in URLs that are not https, in the desktop app and in the CLI, so it needs the HTTPS profile: [https.md](https.md).
- **Codex** works over `http://localhost`. `codex mcp add` already starts the OAuth login and gives up after a few minutes if the browser step is not completed; `codex mcp login google-multi` prints the authorization URL again. Tested with codex-cli 0.155.1 on macOS: Codex picked CIMD with `https://chatgpt.com/oauth/codex/client.json`, the login succeeded and a tool call worked. With upstream's default allowlist (`claude.ai` only) the server answers `400 invalid_client` ("CIMD rejected: issuer=https://chatgpt.com not allowlisted"), which is why `compose.yaml` adds `chatgpt.com`. If registration still fails, force Dynamic Client Registration with `codex mcp login google-multi --oauth-client-registration dcr`.

ChatGPT *web* is not supported: it needs a public HTTPS URL and plugin packaging.

## Tips

- In the Claude desktop app's MCP servers dialog, **Re-authenticate** and **Clear authentication** apply to OAuth servers only. A token-mode server needs neither: it shows Connected, and pressing Re-authenticate would only start an OAuth flow that Claude Code refuses on `http://` ("Refused to open sign-in URL ... must be https"). When the token expires, run `python3 scripts/setup.py` again instead.
- Do not put write tools on auto-approve. See the safety notes in the [README](../README.md).
- To tell the assistant which account to use, name the alias ("use `work`").
