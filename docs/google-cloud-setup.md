# Google Cloud setup (one time, ~10 minutes)

Every app that talks to Gmail/Drive through OAuth needs an OAuth client from some Google Cloud project, so Google knows which app is asking. Claude's and Codex's built-in connectors use the vendor's own client; here you create yours. It is free and needs no billing account. The kit has no server of its own: OAuth tokens are stored on your machine and sent only to Google's APIs.

## 0. Pick the audience

| Your accounts | Choose | What it means |
| --- | --- | --- |
| All in **one Google Workspace organization** | **Internal** | Only users of that org can authorize. No verification, no "unverified app" screen, no 7-day Testing expiry, no user cap. |
| Personal Gmail, or Workspace accounts from **different organizations** | **External**, then publish to **In production** | Works for any Google account. Shows an "unverified app" screen (Advanced -> Continue). Lifetime cap of 100 users. |

Internal needs a project created under a Workspace organization (sign in with a Workspace account when creating it). Personal Gmail accounts have no organization and can only create External.

A shared client cannot be shipped with this kit: a Web client's secret must stay private, and an unverified public app is capped at 100 users. Each user creates their own.

## 1. Create the project

https://console.cloud.google.com/projectcreate - pick a name (for example `claude-mcp`). Note the project ID.

## 2. Enable the APIs (one link)

Replace `PROJECT_ID`, open the link, press **Next**, then **Enable**:

```
https://console.cloud.google.com/flows/enableapi?apiid=gmail.googleapis.com,drive.googleapis.com,sheets.googleapis.com,docs.googleapis.com,calendar-json.googleapis.com&project=PROJECT_ID
```

## 3. Configure the consent screen

https://console.cloud.google.com/auth/overview/create?project=PROJECT_ID

1. App name and support email (yours). The app name is what Google shows on the consent screen and in each account's list of third-party access, so make it say what it is, for example `Google multi-account MCP (local)`. Google lists one entry per OAuth client, never per AI tool, so it cannot show whether Claude Code or Codex used it.
2. Audience: **Internal** or **External** (step 0).
3. Contact email, accept the *Google API Services User Data Policy*, **Create**.

Leave the logo empty: for External apps in production, a logo makes Google require brand verification.

## 4. External only: test users (needed while the app is in Testing)

https://console.cloud.google.com/auth/audience?project=PROJECT_ID -> **Test users** -> **Add users**: every account you will connect. If you publish right away (step 6) you can skip this, but the app starts in Testing, so adding them is the safe order.

## 5. Create the client

https://console.cloud.google.com/auth/clients/create?project=PROJECT_ID

- Application type: **Web application**
- Authorized redirect URI: `http://localhost:4243/callback`
  (also `https://localhost:4244/callback` if you use the HTTPS profile, see [https.md](https.md))
- **Create**, then copy the **Client ID** and **Client secret** right away. The secret is not shown again; if you lose it, create a new one.

Put them in `.env` (`scripts/set-env.py` does it without echoing the secret).

## 6. External only: publish

https://console.cloud.google.com/auth/audience?project=PROJECT_ID -> **Publish app** -> **In production**.

While the app is in *Testing*, Google expires refresh tokens after **7 days** and you must re-authorize every account weekly. In production that Testing expiry no longer applies. Tokens can still stop working for other reasons: you revoke access, the account password changes, an admin policy changes, or the grant goes unused for a long time.

If **Publish app** is disabled, Google lists what is missing on the *Branding* page. Complete it without adding a logo.

## 7. Workspace admins

If a domain restricts third-party apps, an admin of that domain must allow the client: Admin console -> Security -> Access and data control -> API controls -> **App access control** -> add the Client ID as **Trusted**. This is per domain; one client works across domains once each admin allows it.

## Limits to know

- Unverified apps show a warning and are capped at 100 users over the app's lifetime.
- Gmail and full-Drive scopes are *restricted*; removing the cap and the warning requires Google verification, which can include a paid security assessment. Not needed for personal use.
- OAuth clients that stay unused for six months can be deleted by Google automatically; you would then create a new client and re-authorize.
- All users of your client share its API quotas.
- Consent asks for all of the server's base scopes (including Contacts, Tasks and Meet) whatever tools you enable.
