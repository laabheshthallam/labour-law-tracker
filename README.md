# 🇮🇳 India & Gujarat Labour Law Tracker

A real-time regulatory intelligence and compliance tracking web application for **Indian Labour Laws, EPFO / PF, ESIC, Gratuity, EPS Pension Changes, 4 Labour Codes, State-Specific Policies, Gig Economy Regulations, Remote & Hybrid Work, and Official Gazette Circulars**.

> **Built with Pure HTML, CSS, and JavaScript** on the frontend for instant loading in any browser, with automated daily scraping at **6:00 PM IST (18:00 IST)**, Supabase Auth & Database syncing, Telegram Bot alerts, and Gmail HTML digests.

---

## 🌟 Key Features

### 1. Pure HTML, CSS & JavaScript Frontend
- **No Python web server or backend runtime required to view or host the website.**
- Runs directly by opening `index.html` in your browser, or hosting on **GitHub Pages**, **Vercel**, **Netlify**, or **Cloudflare Pages**.
- Responsive, modern user interface with light & dark theme support.

### 2. Concise 40-50 Words Summary Boxes
- Every legal update, circular, and news article is summarized into a crisp **~40-50 words** box highlighting:
  - What statutory rule or policy changed.
  - Practical compliance implications for HR, payroll, and legal teams.
- Each box includes a direct **"Read More" / "Open Source"** button linking to the original government gazette, court judgment, or news publication.

### 3. Comprehensive Multi-Dimensional Filters
- **📍 State-Wise Policy Filter**: Filter by Gujarat, Jammu & Kashmir, Maharashtra, Karnataka, Tamil Nadu, Delhi / NCR, Uttar Pradesh, Rajasthan, Telangana, and Central / National.
- **🏷️ Law Area Filter**:
  - **PF / EPFO**: UAN updates, PF withdrawal rules, auto-settlement, interest rates.
  - **ESI / ESIC**: Wage ceilings, 50% wage rule compliance, medical benefits.
  - **EPS (Pension) Changes**: Minimum pension increase proposals, higher pension calculation circulars.
  - **Gratuity**: 1-year gratuity rules for fixed-term contracts, calculation formulas.
  - **Labour Codes**: Code on Wages, Social Security Code, Industrial Relations Code, OSH Code (Central vs. State final rules).
  - **Minimum Wages & VDA**: Semi-annual Variable Dearness Allowance revisions by state.
  - **Gig Economy & Platform Workers**: Social security boards, aggregator fees, Karnataka / Rajasthan / Telangana Gig Acts.
  - **Remote & Hybrid Work**: SEZ Rule 43A guidelines, cross-border tax, and "work from anywhere" compliance.
  - **Gazettes & Circulars**: Ministry of Labour & Employment (MoLE), EPFO, ESIC, and State Labour Gazettes.
  - **Shops & Establishments & Factories Act**: Applicability thresholds, 24/7 operating rules, overtime limits.
- **🏭 Sector Filter**: IT / ITES & Startups, Gig & Logistics / Quick Commerce, Manufacturing, Textile & Garments, Construction, BFSI, Retail & E-commerce, Healthcare.
- **📅 Time Period Filter**: All Time (Historical from October 2025 to Present), Today (Last 24 Hours), Last 7 Days, Last 30 Days, Last 3 Months, Last Year.
- **🔍 Full-Text Live Search**: Instant searching across titles, summaries, sources, categories, and states with live result count.
- **⭐ Bookmarking**: Save important articles locally or sync to your Supabase account.

### 4. Dynamic "Add Sources" Feature (e.g. Daily Excelsior)
- Suppose the tracker doesn't currently monitor a specific regional publication (e.g. *Daily Excelsior*).
- Simply paste the link `https://www.dailyexcelsior.com/cs-atal-dulloo-reviews-implementation-of-new-labour-codes-in-jk/` into the **"Add Source"** box and click **"Add This Source"**.
- **What happens automatically:**
  1. The article appears **immediately** on your tracker dashboard.
  2. The source domain (`dailyexcelsior.com`) and search query are registered permanently in `data/sources.json` and Supabase.
  3. Every future daily 6:00 PM update cycle will automatically search and reference *Daily Excelsior* for labour, PF, and wage updates.

### 5. Historical Data Archive (October 2025 to Present)
- Pre-loaded with comprehensive, verified updates covering:
  - October 2025 - Present EPFO higher pension developments and interest crediting.
  - 4 Labour Codes central rules gazette and state-level rollout audits.
  - Gujarat Shops & Establishments amendments and minimum wage notifications.
  - J&K Labour Code review under Chief Secretary Atal Dulloo.
  - State gig worker acts and platform welfare fee rules.

### 6. Automated Daily 6:00 PM IST Scraper, Telegram & Gmail Alerts
- Runs automatically every evening at **18:00 IST (6:00 PM IST)** via GitHub Actions.
- Dispatches a structured **Telegram Bot message** and a responsive **Gmail HTML digest** containing today's new updates with direct source links.

---

## 🚀 Quick Start (Running Locally)

### Option A: Open Directly in Your Browser (No Setup Required)
1. Double-click `index.html` (or right-click &rarr; *Open with Browser*).
2. That's it! All search, filtering, and bookmarking features work immediately using the client-side data archive.

### Option B: Using VS Code Live Server or Local Static Server
```bash
# Using Python's built-in HTTP server
python3 -m http.server 8000

# Open in your browser:
# http://localhost:8000
```

---

## ☁️ Deployment & Free GitHub Pages Hosting

### Step 1: Push to GitHub
1. Create a repository on [GitHub](https://github.com).
2. Push all files from this project folder into your repository.

### Step 2: Enable GitHub Pages
1. In your GitHub repository, go to **Settings &rarr; Pages**.
2. Under **Build and deployment &rarr; Source**, choose **Deploy from a branch**.
3. Select Branch: `main`, Folder: `/` (root) or `/docs`, and click **Save**.
4. GitHub will provide your live URL (e.g., `https://username.github.io/gujarat-labour-tracker/`).

---

## 🔐 Supabase Setup (Authentication & Database)

You can connect Supabase to enable User Sign Up / Sign In, sync custom sources across devices, and store bookmarks in the cloud.

### 1. Create a Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a free account.
2. Click **New Project**, name it e.g. `labour-law-tracker`, set a database password, and choose region (e.g. `Mumbai / ap-south-1`).

### 2. Run the SQL Schema
1. In your Supabase Dashboard, click on the **SQL Editor** tab on the left menu.
2. Open the file [`supabase-schema.sql`](file:///home/laabhesh/Downloads/gujarat-labour-tracker/supabase-schema.sql) in this repository.
3. Copy its entire content, paste it into the Supabase SQL Editor, and click **Run**.
4. This will automatically create the `articles`, `custom_sources`, `user_bookmarks`, and `subscribers` tables with Row Level Security (RLS) policies.

### 3. Connect Supabase to the Website
1. Go to **Project Settings &rarr; API** in Supabase.
2. Copy your **Project URL** and **anon public Key**.
3. On your tracker website:
   - Click the **🔐 Sign In / Supabase** button in the navbar.
   - Switch to the **⚙️ Supabase Keys** tab.
   - Paste your **Supabase URL** and **Anon Key**, then click **Save Supabase Connection**.
4. You can now use **Sign Up** and **Sign In** to create user accounts!

---

## 🤖 Telegram Bot & Gmail Digest Setup

To receive automated alerts every evening at 6:00 PM IST:

### 1. Telegram Bot Setup
1. Open Telegram and search for **@BotFather**.
2. Send `/newbot`, choose a name and username, and copy the **Bot Token** (e.g. `123456789:AAxxxxxxxxxxxxxxxxxxxxxx`).
3. Send any message to your new bot (e.g. "hi") so it can message you.
4. Get your numeric **Chat ID**: message **@userinfobot** on Telegram and copy your ID (e.g. `987654321`).

### 2. Gmail App Password Setup
1. Go to your [Google Account &rarr; Security](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is enabled.
3. Go to [App Passwords](https://myaccount.google.com/apppasswords).
4. Create an App Password named `Labour Law Tracker` and copy the 16-character code.

### 3. Add Secrets to GitHub Repository
In your GitHub repo, go to **Settings &rarr; Secrets and variables &rarr; Actions &rarr; New repository secret** and add:

| Secret Name | Description | Example |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `123456789:AA...` |
| `TELEGRAM_CHAT_ID` | Your numeric Telegram chat ID | `987654321` |
| `EMAIL_ADDRESS` | Gmail address sending the digest | `yourname@gmail.com` |
| `EMAIL_APP_PASSWORD` | 16-character Gmail App Password | `abcd efgh ijkl mnop` |
| `EMAIL_TO` | Recipient email(s), comma-separated | `hr@company.com, legal@company.com` |
| `SUPABASE_URL` | *(Optional)* Supabase Project URL | `https://xyz.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | *(Optional)* Supabase Service Role Key | `eyJ...` |
| `ANTHROPIC_API_KEY` | *(Optional)* For AI-enhanced summaries | `sk-ant-...` |

---

## ⏰ Automated 6:00 PM IST Daily Execution

The GitHub Actions workflow in [`.github/workflows/daily-digest.yml`](file:///home/laabhesh/Downloads/gujarat-labour-tracker/.github/workflows/daily-digest.yml) runs every day at **18:00 IST (6:00 PM IST)**:
1. Fetches news from Google News RSS, EPFO, ESIC, Gazette portals, and all user-added sources (like *Daily Excelsior*).
2. Generates 40-50 words compliance summaries.
3. Saves new articles into `data/archive.json` and Supabase.
4. Sends the daily digest to Telegram and Gmail.
5. Commits the updated archive back to your GitHub repo so the website stays up-to-date automatically.

### Running Manually On-Demand:
- **From GitHub**: Go to **Actions &rarr; Daily Labour Law Digest & Tracker Sync &rarr; Run workflow**.
- **From Command Line**:
  ```bash
  python3 updater.py
  ```

---

## 📁 Project Structure

```
.
├── index.html                   # Pure HTML5 main tracker dashboard
├── sources.html                 # Dedicated sources management hub
├── css/
│   └── style.css                # Modern responsive stylesheet (light/dark theme)
├── js/
│   ├── app.js                   # Client application logic & dynamic filters
│   ├── sources-manager.js       # Dynamic URL parsing & source management
│   └── supabase-client.js       # Supabase Auth & Database sync module
├── data/
│   ├── archive.json             # Historical & real-time updates archive (Oct 2025 - Present)
│   └── sources.json             # Monitored publications (Daily Excelsior, PIB, EPFO, etc.)
├── docs/                        # Mirrored static build for GitHub Pages hosting
├── updater.py                   # Automated daily 6:00 PM scraper & digest engine
├── main.py                      # Updater entrypoint
├── config.yaml                  # Scraper configuration, queries, and categories
├── supabase-schema.sql          # Ready-to-use Supabase SQL script
├── requirements.txt             # Python dependencies for scraper
└── .github/workflows/
    └── daily-digest.yml         # GitHub Action scheduled at 18:00 IST (6:00 PM)
```

---

## 📄 License
MIT License. Open-source for HR professionals, legal practitioners, and compliance teams.
