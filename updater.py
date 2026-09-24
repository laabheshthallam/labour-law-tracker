#!/usr/bin/env python3
"""
Gujarat & India Labour Law Tracker - Background Scraper & Digest Notifier
=========================================================================
Runs automatically every day at 18:00 IST (6:00 PM IST) via GitHub Actions
or on-demand.

Key Features:
- Fetches real-time labour, PF, ESI, gratuity, EPS, gig worker, and remote work updates.
- Supports dynamically added sources (e.g., Daily Excelsior, regional news, government gazettes).
- Summarizes each update into approximately 40-50 words with HR/compliance focus.
- Automatically tags State, Law Category, and Sector.
- Stores data into data/archive.json and optional Supabase PostgreSQL database.
- Dispatches instant Telegram Bot messages and rich Gmail HTML digests.
"""

import os
import re
import sys
import json
import html
import hashlib
import smtplib
import urllib.parse
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import yaml
import requests
import feedparser

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
SOURCES_PATH = os.path.join(BASE_DIR, "data", "sources.json")
ARCHIVE_PATH = os.path.join(BASE_DIR, "data", "archive.json")
DOCS_ARCHIVE_PATH = os.path.join(BASE_DIR, "docs", "data", "archive.json")
DOCS_SOURCES_PATH = os.path.join(BASE_DIR, "docs", "data", "sources.json")

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"

BOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

def log(msg):
    print(f"[{now_ist().strftime('%Y-%m-%d %H:%M:%S IST')}] {msg}", flush=True)


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_archive():
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_archive(archive):
    os.makedirs(os.path.dirname(ARCHIVE_PATH), exist_ok=True)
    with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

    # Also mirror into docs/data/ for GitHub Pages
    try:
        os.makedirs(os.path.dirname(DOCS_ARCHIVE_PATH), exist_ok=True)
        with open(DOCS_ARCHIVE_PATH, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Warning: Could not mirror archive to docs/data: {e}")


def load_sources():
    if os.path.exists(SOURCES_PATH):
        with open(SOURCES_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_sources(sources):
    os.makedirs(os.path.dirname(SOURCES_PATH), exist_ok=True)
    with open(SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    try:
        os.makedirs(os.path.dirname(DOCS_SOURCES_PATH), exist_ok=True)
        with open(DOCS_SOURCES_PATH, "w", encoding="utf-8") as f:
            json.dump(sources, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Warning: Could not mirror sources to docs/data: {e}")


def clean_html(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_id(link):
    return hashlib.md5(link.strip().encode("utf-8")).hexdigest()


# ----------------------------------------------------------------
# Classification & Tagging Rules
# ----------------------------------------------------------------

STATE_MAPPINGS = [
    (["gujarat", "ahmedabad", "surat", "vadodara", "rajkot", "gandhinagar", "vapi", "glwb"], "Gujarat"),
    (["jammu", "kashmir", "j&k", "atal dulloo", "srinagar"], "Jammu & Kashmir"),
    (["maharashtra", "mumbai", "pune", "nagpur", "thane", "mahakamgar"], "Maharashtra"),
    (["karnataka", "bengaluru", "bangalore", "mysuru"], "Karnataka"),
    (["tamil nadu", "chennai", "coimbatore"], "Tamil Nadu"),
    (["delhi", "ncr", "noida", "gurugram", "gurgaon", "faridabad"], "Delhi / NCR"),
    (["uttar pradesh", "lucknow", "kanpur"], "Uttar Pradesh"),
    (["rajasthan", "jaipur"], "Rajasthan"),
    (["telangana", "hyderabad"], "Telangana"),
    (["west bengal", "kolkata"], "West Bengal"),
    (["haryana"], "Haryana"),
]

CATEGORY_MAPPINGS = [
    (["epfo", "provident fund", " pf ", "pf scheme", "uan", "edli", "passbook", "epf"], "PF / EPFO"),
    (["eps-95", "eps 95", "pension scheme", "higher pension", "eps pension", "minimum pension rs 7500"], "EPS (Pension) Changes"),
    (["esic", "esi contribution", "employee state insurance", " esi ", "atal beemit"], "ESI / ESIC"),
    (["gratuity", "continuous service", "terminal benefit", "gratuity act"], "Gratuity"),
    (["gig worker", "platform worker", "aggregator", "swiggy", "zomato", "delivery partner", "quick commerce", "dark store", "ride hailing"], "Gig Economy & Platform Workers"),
    (["remote work", "hybrid work", "work from anywhere", "wfh", "sez rule 43a", "cross-border tax", "telecommuting"], "Remote & Hybrid Work"),
    (["minimum wage", "wage rate", "vda", "dearness allowance", "special allowance"], "Minimum Wages"),
    (["labour code", "labor code", "wage code", "industrial relations code", "occupational safety code", "social security code", "osh code"], "Labour Codes"),
    (["shops and establishment", "shop and establishment", "commercial establishment"], "Shops & Establishment Act"),
    (["factories act", "factory act", "occupational health", "boiler"], "Factories Act"),
    (["gazette", "notification no", "pib", "circular no", "ministry of labour"], "Gazette / Notifications"),
    (["maternity benefit", "pregnancy", "creche", "posh"], "Maternity & Welfare"),
    (["trade union", "strike", "lockout", "industrial dispute"], "Trade Unions"),
    (["apprentice", "apprenticeship"], "Apprenticeship"),
]

SECTOR_MAPPINGS = [
    (["gig", "delivery", "aggregator", "logistics", "quick commerce", "e-commerce", "ecommerce", "courier"], "Gig & Logistics"),
    (["software", "it/ites", "tech company", "startup", "information technology", "bpo", "kpo"], "IT / ITES & Startups"),
    (["textile", "garment", "apparel", "spinning", "weaving"], "Textile & Garments"),
    (["manufactur", "factory", "industrial", "chemical", "pharma", "engineering", "automobile"], "Manufacturing"),
    (["construction", "real estate", "building", "infrastructure"], "Construction"),
    (["banking", "financial services", "nbfc", "fintech", "insurance"], "BFSI"),
    (["retail", "mall", "store", "supermarket", "hospitality", "hotel", "restaurant"], "Retail & E-commerce"),
    (["healthcare", "hospital", "nursing home", "clinical"], "Healthcare"),
]


def infer_tags(title, summary, source_name=""):
    text = f"{title or ''} {summary or ''} {source_name or ''}".lower()

    # Detect State
    state = "National / Central"
    for keywords, label in STATE_MAPPINGS:
        if any(k in text for k in keywords):
            state = label
            break

    # Detect Law Category
    category = "Labour Codes"
    for keywords, label in CATEGORY_MAPPINGS:
        if any(k in text for k in keywords):
            category = label
            break

    # Detect Sector
    sector = "General / All Sectors"
    for keywords, label in SECTOR_MAPPINGS:
        if any(k in text for k in keywords):
            sector = label
            break

    return {"state": state, "category": category, "sector": sector}


# ----------------------------------------------------------------
# Summarizer (Target: ~40-50 words)
# ----------------------------------------------------------------

def summarize_45_words(title, raw_text):
    """Summarizes an article into approximately 40-50 words focused on HR/compliance impact."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 120,
                    "messages": [{
                        "role": "user",
                        "content": (
                            "Write a concise, factual 40-50 words summary for an Indian HR, labour law, and compliance digest. "
                            "Highlight the core statutory rule, compliance deadline, or worker benefit. "
                            "Output only the 40-50 word summary without any preamble or formatting.\n\n"
                            f"Title: {title}\nContent: {raw_text[:900]}"
                        ),
                    }],
                },
                timeout=15,
            )
            if resp.ok:
                data = resp.json()
                text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
                res = " ".join(text_blocks).strip()
                if len(res.split()) >= 25:
                    return res
        except Exception as e:
            log(f"Anthropic summarization error: {e}")

    # Fallback smart extraction
    cleaned = clean_html(raw_text)
    if not cleaned or len(cleaned) < 30:
        cleaned = f"Official update regarding {title}. Review compliance obligations, notification details, and operational mandates directly from the original publication."

    words = cleaned.split()
    if len(words) > 50:
        words = words[:48]
        summary = " ".join(words).rstrip(",;:-") + "..."
    elif len(words) < 25:
        summary = f"{cleaned} Employers and compliance managers are advised to evaluate potential impact on statutory payroll filings and workforce policies."
    else:
        summary = " ".join(words)

    return summary


# ----------------------------------------------------------------
# Dynamic Custom Sources Handler (e.g. Daily Excelsior)
# ----------------------------------------------------------------

def parse_and_register_custom_url(url):
    """Parses an arbitrary link (e.g. Daily Excelsior) and builds a monitored source entry."""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.replace("www.", "").lower()

    name_map = {
        "dailyexcelsior.com": "Daily Excelsior",
        "economictimes.indiatimes.com": "The Economic Times",
        "livemint.com": "Livemint",
        "business-standard.com": "Business Standard",
        "thehindu.com": "The Hindu",
        "barandbench.com": "Bar and Bench",
        "livelaw.in": "LiveLaw",
        "pib.gov.in": "Press Information Bureau (PIB)",
        "epfindia.gov.in": "EPFO Official",
        "esic.gov.in": "ESIC Portal",
        "egazette.gov.in": "Gazette of India",
        "labour.gujarat.gov.in": "Gujarat Labour Dept",
    }
    source_name = name_map.get(domain, domain.capitalize())

    # Build automated domain query
    query = f"site:{domain} (labour OR \"labour codes\" OR pf OR epfo OR esic OR gratuity OR \"minimum wages\" OR \"gig workers\")"

    return {
        "id": f"src-{domain.replace('.', '-')}",
        "name": source_name,
        "domain": domain,
        "url": url,
        "type": "domain_search",
        "query": query,
        "active": True,
        "added_at": now_ist().strftime("%Y-%m-%d"),
    }


def fetch_url_metadata(url):
    """Extracts title and content from a specific web link."""
    try:
        resp = requests.get(url, timeout=12, headers=BOT_HEADERS)
        if resp.ok:
            text = resp.text
            m_title = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
            title = clean_html(m_title.group(1)) if m_title else "Labour Law Update"
            if " - " in title:
                title = title.split(" - ")[0].strip()

            m_desc = (re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', text, re.IGNORECASE)
                      or re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', text, re.IGNORECASE))
            desc = clean_html(m_desc.group(1)) if m_desc else ""

            domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
            return {"title": title, "summary": desc, "source": domain}
    except Exception as e:
        log(f"Failed to fetch metadata for {url}: {e}")
    return None


# ----------------------------------------------------------------
# Fetching Feeds & Google News
# ----------------------------------------------------------------

def fetch_rss_query(query, default_category=None, default_state=None):
    rss_url = GOOGLE_NEWS_RSS.format(q=urllib.parse.quote(query))
    items = []
    try:
        parsed = feedparser.parse(rss_url)
        for entry in parsed.entries[:15]:
            link = entry.get("link", "").strip()
            if not link:
                continue

            raw_title = clean_html(entry.get("title", ""))
            source_name = "News Source"
            title = raw_title
            if " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                title = parts[0].strip()
                source_name = parts[1].strip()

            raw_summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
            published = entry.get("published", "") or now_ist().strftime("%Y-%m-%d")

            items.append({
                "title": title,
                "link": link,
                "source": source_name,
                "raw_summary": raw_summary,
                "published_raw": published,
                "hint_category": default_category,
                "hint_state": default_state,
            })
    except Exception as e:
        log(f"Error fetching Google RSS query '{query}': {e}")
    return items


# ----------------------------------------------------------------
# Supabase Integration
# ----------------------------------------------------------------

def sync_to_supabase(articles, custom_sources):
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        log("Supabase credentials not found. Storing locally in data/archive.json.")
        return

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    try:
        # Upsert latest articles
        payload = []
        for a in articles[:100]:
            payload.append({
                "id": a["id"],
                "title": a["title"],
                "link": a["link"],
                "source": a["source"],
                "category": a["category"],
                "state": a["state"],
                "sector": a.get("sector", "General / All Sectors"),
                "summary": a["summary"],
                "added_date": a["added_date"],
            })

        resp = requests.post(
            f"{supabase_url.rstrip('/')}/rest/v1/articles",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if resp.ok:
            log(f"Successfully synced {len(payload)} articles to Supabase.")
        else:
            log(f"Supabase sync response: {resp.status_code} {resp.text}")
    except Exception as e:
        log(f"Supabase sync error: {e}")


# ----------------------------------------------------------------
# Telegram & Gmail Notifications
# ----------------------------------------------------------------

def send_telegram_digest(new_items, date_str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("Telegram bot token or chat ID not set. Skipping Telegram notification.")
        return False

    lines = [
        f"🇮🇳 *India & Gujarat Labour Law Daily Digest*",
        f"📅 *{date_str} (6:00 PM IST)*",
        f"✨ *{len(new_items)} New Updates Tracked*",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]

    for i, item in enumerate(new_items[:8], 1):
        lines.append(f"\n*{i}. {item['title']}*")
        lines.append(f"📍 `{item['state']}` | 🏷️ `{item['category']}` | 📰 _{item['source']}_")
        lines.append(f"{item['summary']}")
        lines.append(f"[🔗 Read Full Source]({item['link']})")

    if len(new_items) > 8:
        lines.append(f"\n_...and {len(new_items) - 8} more updates on your tracker website._")

    message = "\n".join(lines)

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        if resp.ok:
            log("Telegram digest sent successfully.")
            return True
        else:
            log(f"Telegram send failed: {resp.status_code} {resp.text}")
    except Exception as e:
        log(f"Telegram exception: {e}")
    return False


def send_gmail_digest(new_items, date_str, site_url=""):
    address = os.environ.get("EMAIL_ADDRESS")
    password = os.environ.get("EMAIL_APP_PASSWORD")
    to_emails = os.environ.get("EMAIL_TO")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    if not address or not password or not to_emails:
        log("Gmail credentials (EMAIL_ADDRESS / EMAIL_APP_PASSWORD / EMAIL_TO) not configured. Skipping email.")
        return False

    recipients = [e.strip() for e in to_emails.split(",") if e.strip()]

    # Build clean HTML email
    items_html = ""
    for item in new_items:
        items_html += f"""
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:18px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="display:flex;gap:8px;margin-bottom:8px;font-size:12px;font-weight:700;">
                <span style="background:#e0f2fe;color:#0369a1;padding:3px 8px;border-radius:6px;">📍 {html.escape(item['state'])}</span>
                <span style="background:#fef3c7;color:#92400e;padding:3px 8px;border-radius:6px;">🏷️ {html.escape(item['category'])}</span>
                <span style="background:#f1f5f9;color:#475569;padding:3px 8px;border-radius:6px;">🏭 {html.escape(item.get('sector', 'General'))}</span>
            </div>
            <h3 style="margin:0 0 8px;color:#0f172a;font-size:16px;line-height:1.4;">{html.escape(item['title'])}</h3>
            <p style="margin:0 0 12px;color:#334155;font-size:14px;line-height:1.6;">{html.escape(item['summary'])}</p>
            <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#64748b;">
                <span>Source: <strong>{html.escape(item['source'])}</strong> &middot; {item['added_date']}</span>
                <a href="{item['link']}" style="background:#0284c7;color:#ffffff;text-decoration:none;padding:6px 14px;border-radius:6px;font-weight:700;display:inline-block;">Read Full Article &rarr;</a>
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:0;padding:24px;">
        <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #cbd5e1;">
            <div style="background:linear-gradient(135deg, #0f172a 0%, #0369a1 100%);color:#ffffff;padding:28px 24px;text-align:center;">
                <h1 style="margin:0 0 6px;font-size:22px;letter-spacing:-0.3px;">India &amp; Gujarat Labour Law Tracker</h1>
                <p style="margin:0;opacity:0.9;font-size:14px;">Daily Compliance &amp; Policy Digest &middot; {date_str} (6:00 PM IST)</p>
            </div>
            <div style="padding:24px;background:#f8fafc;">
                <p style="margin:0 0 18px;font-size:15px;color:#334155;">Here are the latest labour law, PF, ESIC, gratuity, state policy, and workforce updates tracked today:</p>
                {items_html}
                {f'<div style="text-align:center;margin-top:24px;"><a href="{site_url}" style="color:#0369a1;font-weight:700;text-decoration:none;font-size:14px;">&larr; View Live Interactive Web Tracker &rarr;</a></div>' if site_url else ''}
            </div>
            <div style="background:#f1f5f9;padding:16px 24px;text-align:center;font-size:12px;color:#64748b;border-top:1px solid #e2e8f0;">
                Automated daily digest sent at 6:00 PM IST. Tracked sources include PIB, EPFO, ESIC, Gazette of India, Daily Excelsior, and state labour portals.
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🇮🇳 Labour Law Daily Digest: {len(new_items)} New Updates ({date_str})"
    msg["From"] = address
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(address, password)
            server.sendmail(address, recipients, msg.as_string())
        log(f"Gmail digest successfully sent to {len(recipients)} recipient(s).")
        return True
    except Exception as e:
        log(f"Gmail digest sending failed: {e}")
        return False


# ----------------------------------------------------------------
# Main Run Loop
# ----------------------------------------------------------------

def run_tracker():
    log("==========================================================")
    log("Starting Gujarat & India Labour Law Tracker Sync (6:00 PM IST)")
    log("==========================================================")

    config = load_config()
    archive = load_archive()
    sources = load_sources()
    existing_links = {a["link"].strip() for a in archive}

    log(f"Loaded {len(archive)} existing archived updates and {len(sources)} tracked sources.")

    # 1. Fetch search queries from config.yaml
    raw_entries = []
    for q in config.get("search_queries", []):
        fetched = fetch_rss_query(q["query"], default_category=q.get("category"), default_state=q.get("state"))
        raw_entries.extend(fetched)

    # 2. Fetch custom sources (including Daily Excelsior and user-added domains)
    for s in sources:
        if s.get("active", True) and s.get("query"):
            fetched = fetch_rss_query(s["query"], default_category=s.get("category"), default_state=s.get("state"))
            raw_entries.extend(fetched)

    log(f"Collected {len(raw_entries)} potential entries from Google News & feeds.")

    # 3. Deduplicate and create structured items
    new_items = []
    seen_in_run = set()
    today_iso = now_ist().strftime("%Y-%m-%d")

    for entry in raw_entries:
        link = entry["link"].strip()
        if not link or link in existing_links or link in seen_in_run:
            continue
        seen_in_run.add(link)

        tags = infer_tags(entry["title"], entry["raw_summary"], entry["source"])
        if entry.get("hint_state"):
            tags["state"] = entry["hint_state"]
        if entry.get("hint_category"):
            tags["category"] = entry["hint_category"]

        summary = summarize_45_words(entry["title"], entry["raw_summary"])

        item = {
            "id": make_id(link),
            "title": entry["title"],
            "link": link,
            "source": entry["source"],
            "category": tags["category"],
            "state": tags["state"],
            "sector": tags["sector"],
            "summary": summary,
            "added_date": today_iso,
            "notified": False,
        }

        new_items.append(item)
        archive.insert(0, item)
        existing_links.add(link)

    log(f"Found {len(new_items)} new verified items for today.")

    # 4. Save updated archive
    save_archive(archive)
    save_sources(sources)

    # 5. Sync to Supabase if configured
    sync_to_supabase(archive, sources)

    # 6. Send Telegram & Gmail digests if there are new items
    if new_items:
        date_display = now_ist().strftime("%d %b %Y")
        site_url = os.environ.get("SITE_URL", "")

        tg_ok = send_telegram_digest(new_items, date_display)
        email_ok = send_gmail_digest(new_items, date_display, site_url)

        for item in new_items:
            if tg_ok or email_ok:
                item["notified"] = True

        save_archive(archive)
    else:
        log("No new updates to notify for today.")

    log("Sync completed successfully.")


if __name__ == "__main__":
    run_tracker()
