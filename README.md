# google-multi-account-mcp

Claude Code and Codex multi-account connector for Google (Gmail and Workspace).

One local MCP server that lets Claude Code or Codex use **several Google accounts at once** (personal Gmail, Workspace accounts from different organizations) across Gmail, Drive, Sheets, Docs and Calendar. The built-in connectors of both tools hold one account each. This kit runs [mcp-google-multi](https://github.com/bakissation/mcp-google-multi) (MIT, by bakissation) in Docker with hardened defaults and a documented setup. It is not affiliated with that project, Anthropic, OpenAI or Google.

- **One server, accounts by alias.** Tell the assistant "use `work`".
- **Your own Google OAuth client.** The kit has no server of its own: tokens are stored on your machine, in a Docker volume, and sent only to Google's APIs.
- **Hardened defaults.** Read-only profile, pinned image digest, non-root, read-only root filesystem, all capabilities dropped, port published on loopback only.

## Requirements

- Docker Engine **28.0.0 or newer** (older engines can expose loopback-published ports to your network) with Compose **2.20 or newer**. Docker Desktop on macOS and Windows, Docker Engine on Linux.
- Windows: run the commands in a **WSL2 shell** and keep this repository inside the WSL filesystem.
- A Google account, and Claude Code and/or Codex.
- Python 3 only for the optional `scripts/set-env.py`.

## Quick start

1. Create your OAuth client: [docs/google-cloud-setup.md](docs/google-cloud-setup.md). An agent with browser control can do the Console steps for you: [docs/automated-setup.md](docs/automated-setup.md).
2. `cp .env.example .env` (macOS/Linux: also `chmod 600 .env`), then fill the four values.
3. `docker compose up -d --wait`
4. Connect your client: [docs/connect-clients.md](docs/connect-clients.md).
5. Authorize each account (the first tool call returns a link; press **Allow**).

The default profile is **read-only**. To let the assistant create and edit, set `GOOGLE_PROFILE=safe-writes` in `.env` and read the notes below first.

## Safety notes

Verified against the upstream v6.0.0 source (tagged 2026-10-14) unless marked otherwise.

- **Writes are off by default.** `safe-writes` allows create/update, and also **sending Gmail, sharing Drive files (including "anyone with the link") and Calendar invitations**. It blocks permanent deletes, privileged scopes and push-channel registration. When you enable writes, set `GOOGLE_OUTBOUND_ALLOWLIST=@your-domain.com` (refuses Gmail recipients, Calendar attendees and Drive grantees outside the list, and the curated `drive_share` tool refuses "anyone" links) and **do not put write tools on auto-approve**.
- **The generic `google_api_call` tool bypasses parts of those protections.** The allowlist only inspects `emailAddress`/`email` fields, so a `drive.permissions.create` with `{"type": "anyone"}` through that tool is not caught, and `GOOGLE_WRITE_DENY` is evaluated against a synthetic name there (for example `drive_create`), so `drive:upload` does not apply to it. If you enable writes, **disable that tool in your client**: Claude Code: add `mcp__google-multi__google_api_call` to `permissions.deny`; Codex: `disabled_tools = ["google_api_call"]` under `[mcp_servers.google-multi]`.
- **Upstream has no path guard on Drive local-file tools.** `drive_upload` and `drive_update` accept a `localPath` and can read any file in the container, including the encrypted tokens and the key beside them. `drive_upload` is denied by default (`GOOGLE_WRITE_DENY=drive:upload`). `drive_update` cannot be denied on its own: the deny glob matches the tool name *and* its verb, so `drive:update` also disables Drive move, permission, comment and revision updates. Gmail attachments are refused inside the config and token directories but can still read other container files, for example the process environment (not verified). The download/export tools can write to arbitrary container paths, which can overwrite the key and break authentication (reported, not verified).
- **Tokens and the key that encrypts them share one volume**, so the encryption protects against a stolen token file, not against anything that can read the whole volume.
- **Scopes are broad.** Consent asks for all base scopes (Gmail modify and send, full Drive, Contacts, Tasks, Meet, ...) whatever `GOOGLE_TOOLSETS` says; the setting only limits which tools are offered.
- **Loopback only.** The server is reachable from your machine only. Do not expose it to a network without a rate limit in front of it.
- **Young upstream.** v6.0.0 is a recent major release with a single maintainer. Review the diff before changing the pinned digest.

## Upgrade and rollback

```bash
docker buildx imagetools inspect ghcr.io/bakissation/mcp-google-multi:X.Y.Z   # copy the index "Digest:" line
# put it in compose.yaml as image: ghcr.io/bakissation/mcp-google-multi:X.Y.Z@sha256:...
docker compose pull && docker compose up -d --wait
```

To roll back, restore the previous image line and run the same commands. The volume (tokens, key) is kept.

## Status

Early. Tested: macOS, Docker Desktop, Claude Code, two Workspace accounts from different organizations. **Not yet tested:** Codex, Windows, Linux, personal Gmail accounts, the HTTPS profile.

## Without Docker

Upstream also runs over stdio with `npx` (Node 22+), which is the simplest single-user option. Its setup is documented upstream and not covered here. ChatGPT web is out of scope: it needs a public HTTPS URL.

## Credits and license

MIT. The server is [bakissation/mcp-google-multi](https://github.com/bakissation/mcp-google-multi); the healthcheck in `compose.yaml` is adapted from its `deploy/compose.yaml`. This repository adds the Compose setup, hardening and documentation. See also [SECURITY.md](SECURITY.md).
