# Automated Google Cloud setup with an agent

An agent with browser control (Claude Code with its built-in browser or the Chrome extension, or Codex / ChatGPT with browser use) can do the Console steps in [google-cloud-setup.md](google-cloud-setup.md) for you. Google exposes no API for the consent screen and Web clients, so the browser is the only automation path.

**Before you start:** be signed in to Google Cloud Console in the agent's browser. The agent must never type your password or MFA code; you sign in yourself. Run `cp .env.example .env` once so the helper script has a file to update.

## Prompt

Replace the bracketed parts and paste:

```text
Set up a Google OAuth client for google-multi-account-mcp by following docs/google-cloud-setup.md in this repo.

Facts: audience = [Internal | External]; accounts to connect = [alias:email, ...]; project = [create "claude-mcp" | existing ID].

Rules:
- Never enter passwords or MFA codes. If the browser asks to sign in, stop and tell me.
- Before each group of state-changing steps (create project, enable APIs, configure consent screen,
  add test users, create client), tell me exactly what you will do and wait for my "yes".
- Do not upload a logo. Do not click "Publish app" unless I ask.
- Never print the client secret in chat. Use the copy button in the "OAuth client created" dialog and pipe the
  clipboard into scripts/set-env.py (macOS: pbpaste, Linux: wl-paste or xclip -o, Windows PowerShell: Get-Clipboard):
    <clipboard command> | python3 scripts/set-env.py GOOGLE_CLIENT_SECRET 'GOCSPX-[A-Za-z0-9_-]{20,}'
    <clipboard command> | python3 scripts/set-env.py GOOGLE_CLIENT_ID '[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com'
  Clear the clipboard afterwards.
- Do not close the "client created" dialog before both values are saved: the secret is shown once.
- When both values are saved, have me run `python3 scripts/setup.py` in a terminal I can type into. It asks for
  the client ID and secret again (Enter keeps what is saved) and for my first Google account (alias + email),
  starts Docker and guides the authorization of each account. Do not edit the other .env values yourself.
- Report what you changed and whether publishing to "In production" is still outstanding (External apps only).
```

## Tips that save time

- `https://console.cloud.google.com/flows/enableapi?apiid=...&project=ID` enables several APIs with one confirmation.
- Prefer element references over pixel coordinates; the dialog's final **Create** button sits near a breadcrumb that is easy to hit by mistake.
- A page's copy button can write to the system clipboard. The regex in `scripts/set-env.py` rejects anything that is not the expected value.
- The console UI changes. If a step does not match, follow the page's wording and report the difference.
