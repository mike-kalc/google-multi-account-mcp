# Optional local HTTPS for OAuth mode (Claude Code only)

**Not needed in the default token mode.** It is only for using the server's own OAuth sign-in from Claude Code: Claude Code refuses to open a sign-in URL that is not https (`Refused to open sign-in URL ...: must be https`, seen in the desktop app and in the CLI). Codex accepts `http://localhost` and ignores `NODE_EXTRA_CA_CERTS`, so this profile is not for Codex.

1. Add `https://localhost:4244/callback` to the client's redirect URIs in Google Cloud.
2. Start with the override file:

   ```bash
   docker compose -f compose.yaml -f compose.https.yaml up -d --wait
   ```

3. Export Caddy's local root certificate:

   ```bash
   docker compose -f compose.yaml -f compose.https.yaml cp caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
   ```

4. Make Claude Code trust it **for that process only**: add to `~/.claude/settings.json`

   ```json
   { "env": { "NODE_EXTRA_CA_CERTS": "/absolute/path/to/caddy-root.crt" } }
   ```

5. Re-register the server (an existing registration with the same name and scope cannot be overwritten):

   ```bash
   claude mcp remove google-multi -s user
   claude mcp add --transport http -s user google-multi https://localhost:4244/mcp
   ```

6. Your **browser** also opens `https://localhost:4244/...` during sign-in and will show a certificate warning, because only Claude Code trusts Caddy's CA. Proceed once for that address, or trust the CA in the browser.

Security note: the CA's private key lives in the `caddy-data` Docker volume. Anyone who obtains it can mint certificates that clients trusting the CA will accept. Prefer the per-process trust above over adding the CA to the system keychain, and remove the setting when you no longer need HTTPS.
