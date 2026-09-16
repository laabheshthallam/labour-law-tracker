# Gujarat & India Labour Law Tracker

Every day this automatically:
1. Searches the web for news and YouTube videos about **PF/EPFO, ESI/ESIC, Gujarat labour law, and central labour codes** (edit the list in `config.yaml`).
2. Writes a short summary for each new item.
3. Sends you a **Telegram message** and an **email digest**.
4. Adds everything to a permanent, searchable **website** (free, hosted on GitHub Pages) so you can always look back.

It costs nothing to run and needs no server — GitHub runs it for you on a timer.

---

## One-time setup (about 20 minutes)

### 1. Get a GitHub account and create a repository
- Go to https://github.com and sign up (free) if you don't have an account.
- Click **New repository**, name it e.g. `labour-law-tracker`, keep it **Public** (needed for free GitHub Pages), click **Create**.
- Upload all the files from this folder into that repository (drag-and-drop works on the GitHub website, via "Add file → Upload files").

### 2. Turn on the website (GitHub Pages)
- In your repo, go to **Settings → Pages**.
- Under "Build and deployment", set **Source: Deploy from a branch**.
- Branch: `main`, Folder: `/docs`. Click **Save**.
- GitHub will give you a URL like `https://YOUR-USERNAME.github.io/labour-law-tracker/` — this is your permanent archive site. It updates itself every day.

### 3. Create a Telegram bot (for instant messages)
- Open Telegram, search for **@BotFather**, start a chat, send `/newbot` and follow the prompts.
- BotFather gives you a **token** like `123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`. Save it.
- Send your new bot any message (e.g. "hi") so it can message you back.
- Then find your **chat ID**: message **@userinfobot** on Telegram and it will reply with your numeric ID.

### 4. Create an email app password (for the email digest)
If using Gmail:
- Go to https://myaccount.google.com/apppasswords (requires 2-Step Verification to be turned on).
- Create an app password named "labour law tracker" — copy the 16-character password.
- (Any other email provider with SMTP + an app password works too; just change `SMTP_HOST`/`SMTP_PORT` if not Gmail.)

### 5. Add your secrets to GitHub
In your repo: **Settings → Secrets and variables → Actions → New repository secret**. Add each of these:

| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | your numeric chat ID |
| `EMAIL_ADDRESS` | the Gmail address sending the digest |
| `EMAIL_APP_PASSWORD` | the 16-character app password |
| `EMAIL_TO` | where to receive it — your email(s), comma-separated if more than one |
| `ANTHROPIC_API_KEY` | *(optional)* — only if you want AI-written summaries instead of the plain news snippet. Get one at https://console.anthropic.com |

Also under **Settings → Secrets and variables → Actions → Variables** tab, optionally add:
| Variable name | Value |
|---|---|
| `SITE_URL` | your GitHub Pages URL from step 2, so the email links to it |

### 6. Run it
- Go to the **Actions** tab in your repo → click **Daily Labour Law Digest** → **Run workflow** → **Run workflow**.
- After a minute or two, check Telegram and your email. Check your Pages URL to see the archive site.
- From now on it runs automatically every day at 9:00 AM IST. No further action needed.

---

## Adding sources from the website (no code editing)
Once GitHub Pages is live, open your site and click **+ Manage Sources** in the header (`your-site-url/admin.html`). From there you can:
- Add a search topic (e.g. "Gujarat apprenticeship rules") with a category label
- Add a direct feed (a specific YouTube channel, blog, or official RSS URL if you find one)
- Remove any source you added
- Trigger an immediate run to test, instead of waiting for the next 9am run

**One-time setup for this page:**
1. Create a GitHub personal access token: go to **github.com/settings/personal-access-tokens** → **Generate new token (fine-grained)**.
2. Set **Repository access** to only this repository.
3. Under **Permissions**, grant **Contents: Read and write** and **Actions: Read and write**. Leave everything else as "No access".
4. Set an expiration (e.g. 90 days — you'll just generate a new one and re-enter it when it expires).
5. Copy the token (starts with `github_pat_...`).
6. On the Manage Sources page, enter your GitHub username, repository name, and this token. It's saved only in your browser (localStorage) — it is never sent anywhere except directly to `api.github.com` from your own browser.

This writes to `data/sources.json` in your repo — a separate file from `config.yaml`, so your hand-edited defaults and comments in `config.yaml` are never touched or overwritten. Both files are combined automatically on every run.

⚠️ Because the token can write to your repo, don't enter it on a shared/public computer, and use a fine-grained token scoped to just this repo (not a classic all-repo token).

## Customizing what it tracks (advanced / manual route)
You can also edit `config.yaml` directly and add or reword lines in the `search_queries` list. Each entry needs:
```yaml
- query: "your search phrase"
  category: "Label shown in digest and website"
```
You can also add direct RSS feeds (e.g. a specific YouTube channel's feed, or an official government feed if you find one) under `rss_feeds`.

To find a YouTube channel's feed URL: open the channel page, view page source, search for `"channelId"`, then use:
`https://www.youtube.com/feeds/videos.xml?channel_id=THAT_ID`

## How summaries are generated
By default, the summary is the news snippet Google News provides, cleaned up. If you add an `ANTHROPIC_API_KEY` secret, it instead asks Claude to write a sharper 2-sentence, HR-relevant summary for every new item — this is optional and costs a small amount per API call (a few paise per item).

## Notes and limitations
- Sources are pulled via Google News search, which covers most mainstream coverage of PF/ESI/labour law but is not an official government feed. Always verify anything material against the primary source (EPFO/ESIC circulars, Gujarat Labour & Employment Department notifications) before acting on it.
- If Telegram or email secrets are missing, that channel is simply skipped (not an error) — you can start with just one and add the other later.
- The workflow only pushes updates back to your repo automatically; it does not need you to keep any app or computer running.
