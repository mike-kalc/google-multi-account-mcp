# Connect Claude Code or Codex

The server listens on `http://localhost:4243/mcp` (loopback only). Always use the host name `localhost`; `127.0.0.1` is rejected by the server's Host check.

## Claude Code

```bash
claude mcp add --transport http -s user google-multi http://localhost:4243/mcp
```

Then inside Claude Code: `/mcp` -> `google-multi` -> **Authenticate**. A browser opens at the Google sign-in of the MCP server's owner gate: sign in with one of the `MCP_OWNER_EMAILS`.

Already registered under that name? Run `claude mcp remove google-multi -s user` first.

If your Claude client refuses http authorization URLs (reported for the desktop UI), use the HTTPS profile: [https.md](https.md).

## Codex (CLI, ChatGPT desktop app, IDE extension)

```bash
codex mcp add google-multi --url http://localhost:4243/mcp
codex mcp login google-multi
```

The server advertises client-metadata-document (CIMD) support, so Codex registers through its ChatGPT-hosted metadata document. `compose.yaml` therefore trusts `chatgpt.com` in `MCP_CIMD_ALLOWED_ISSUERS` (upstream trusts only `claude.ai` by default). If login still fails during client registration, force Dynamic Client Registration:

```bash
codex mcp login google-multi --oauth-client-registration dcr
```

`codex mcp add` already starts the OAuth login and gives up after a few minutes if the browser step is not completed; `codex mcp login google-multi` prints the authorization URL again. Open it in your browser, sign in with one of the `MCP_OWNER_EMAILS` and allow.

Tested with codex-cli 0.155.1 on macOS (default `auto` registration): Codex picked CIMD with `https://chatgpt.com/oauth/codex/client.json`, the login succeeded, and a tool call (`account_list`) worked. With upstream's default allowlist (`claude.ai` only) the server answers `400 invalid_client` ("CIMD rejected: issuer=https://chatgpt.com not allowlisted"), which is why `compose.yaml` adds `chatgpt.com`. Not tested: authorizing a Google account from inside Codex (same flow as Claude Code) and real Gmail/Drive calls. The CLI, desktop app and IDE share one `~/.codex/config.toml`.

ChatGPT *web* is not supported: it needs a public HTTPS URL and plugin packaging.

## Authorize each Google account

The owner sign-in only gates access to the MCP server. Each alias from `GOOGLE_ACCOUNTS` is then authorized separately: the first tool call for an alias without a token returns an error with a signed re-auth link (valid 1 hour). Open it in your browser, pick the account, press **Allow** (External apps show "unverified app": Advanced -> Continue).

Useful tools: `account_list` (aliases and token status), `account_reauth` (new link for an alias).

## Smoke test

Ask the assistant to list your Google accounts, then to read-only search one mailbox per alias.

## Tips

- Do not put write tools on auto-approve. See the safety notes in the [README](../README.md).
- To tell the assistant which account to use, name the alias ("use `work`").
