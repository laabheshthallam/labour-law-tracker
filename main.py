#!/usr/bin/env python3
"""
Gujarat / India Labour Law Tracker
-----------------------------------
Fetches news + video links about Indian labour law, PF, ESI,
and Gujarat-specific labour policy, summarizes each item,
sends a daily digest via Telegram + Email, and rebuilds a
static archive website (docs/index.html) for GitHub Pages.

Run with: python main.py
Configuration: config.yaml
Secrets/credentials: environment variables (see README.md)
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
SITE_PATH = os.path.join(BASE_DIR, "docs", "index.html")
ADMIN_SITE_PATH = os.path.join(BASE_DIR, "docs", "admin.html")

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_archive():
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_sources():
    """Sources added via the website's 'Manage Sources' page.

    Format (list of objects), e.g.:
      {"type": "query", "query": "...", "category": "..."}
      {"type": "feed", "url": "...", "name": "...", "category": "..."}
    """
    if os.path.exists(SOURCES_PATH):
        with open(SOURCES_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                log("WARNING: data/sources.json is malformed, ignoring it this run.")
                return []
    return []


def save_archive(archive):
    os.makedirs(os.path.dirname(ARCHIVE_PATH), exist_ok=True)
    with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)


def clean_html(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_id(link):
    return hashlib.md5(link.encode("utf-8")).hexdigest()


def google_news_url(query):
    return GOOGLE_NEWS_RSS.format(q=urllib.parse.quote(query))


# ----------------------------------------------------------------
# Fetching
# ----------------------------------------------------------------

def fetch_entries(url, category, default_source=None):
    """Fetch and normalize entries from a single RSS/Atom feed URL."""
    items = []
    try:
        parsed = feedparser.parse(url)
        feed_title = default_source or parsed.feed.get("title", "Unknown source")
        for entry in parsed.entries:
            link = entry.get("link", "").strip()
            if not link:
                continue
            title = clean_html(entry.get("title", "Untitled"))
            summary_raw = entry.get("summary", "") or entry.get("description", "")
            summary = clean_html(summary_raw)
            # Google News wraps the real source name after " - " in title
            source_name = feed_title
            if " - " in title and default_source is None:
                title, maybe_source = title.rsplit(" - ", 1)
                if len(maybe_source) < 60:
                    source_name = maybe_source
            published = entry.get("published", "") or entry.get("updated", "")
            items.append({
                "title": title.strip(),
                "link": link,
                "source": source_name.strip(),
                "category": category,
                "published_raw": published,
                "raw_summary": summary,
            })
    except Exception as e:
        log(f"WARNING: failed to fetch feed for category '{category}' ({url}): {e}")
    return items


def collect_all_entries(config, sources):
    all_items = []
    for q in config.get("search_queries", []):
        url = google_news_url(q["query"])
        all_items.extend(fetch_entries(url, q["category"]))
    for feed in config.get("rss_feeds", []) or []:
        all_items.extend(fetch_entries(feed["url"], feed["category"], default_source=feed.get("name")))
    # Sources added by users through the website's Manage Sources page
    for s in sources:
        if s.get("type") == "query" and s.get("query") and s.get("category"):
            all_items.extend(fetch_entries(google_news_url(s["query"]), s["category"]))
        elif s.get("type") == "feed" and s.get("url") and s.get("category"):
            all_items.extend(fetch_entries(s["url"], s["category"], default_source=s.get("name")))
    return all_items


# ----------------------------------------------------------------
# Summarization
# ----------------------------------------------------------------

def ai_summarize(title, raw_summary):
    """Use the Anthropic API for a crisp 2-3 sentence summary, if a key is set."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
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
                "max_tokens": 150,
                "messages": [{
                    "role": "user",
                    "content": (
                        "You write short, factual 2-sentence summaries for an HR "
                        "consultant's news digest about Indian labour law, PF, ESI, "
                        "and Gujarat state labour policy. Summarize what this item is "
                        "about and why an HR/compliance professional would care. "
                        "No preamble, no markdown, just the summary text.\n\n"
                        f"Title: {title}\nSnippet: {raw_summary[:800]}"
                    ),
                }],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return " ".join(text_blocks).strip() or None
    except Exception as e:
        log(f"WARNING: AI summarization failed, falling back to snippet: {e}")
        return None


def summarize(item, fallback_len):
    ai = ai_summarize(item["title"], item["raw_summary"])
    if ai:
        return ai
    snippet = item["raw_summary"]
    if len(snippet) > fallback_len:
        snippet = snippet[:fallback_len].rsplit(" ", 1)[0] + "..."
    return snippet or "No summary available - open the link for details."


# ----------------------------------------------------------------
# Notification: Telegram
# ----------------------------------------------------------------

def send_telegram(text_chunks):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("Telegram credentials not set - skipping Telegram send.")
        return False
    ok = True
    for chunk in text_chunks:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            if not resp.ok:
                log(f"Telegram send failed: {resp.status_code} {resp.text}")
                ok = False
        except Exception as e:
            log(f"Telegram send error: {e}")
            ok = False
    return ok


def chunk_text(text, limit=3800):
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:]
    if text.strip():
        chunks.append(text)
    return chunks


# ----------------------------------------------------------------
# Notification: Email
# ----------------------------------------------------------------

def send_email(subject, html_body, plain_body):
    address = os.environ.get("EMAIL_ADDRESS")
    app_password = os.environ.get("EMAIL_APP_PASSWORD")
    to_addrs = os.environ.get("EMAIL_TO")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    if not address or not app_password or not to_addrs:
        log("Email credentials not set - skipping email send.")
        return False

    recipients = [a.strip() for a in to_addrs.split(",") if a.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(address, app_password)
            server.sendmail(address, recipients, msg.as_string())
        return True
    except Exception as e:
        log(f"Email send error: {e}")
        return False


# ----------------------------------------------------------------
# Digest composition
# ----------------------------------------------------------------

def group_by_category(items):
    grouped = {}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
    return grouped


def build_telegram_text(new_items, date_str):
    grouped = group_by_category(new_items)
    lines = [f"*Gujarat & India Labour Law Digest - {date_str}*", ""]
    for category, items in grouped.items():
        lines.append(f"🏷️ *{category}*")
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. [{item['title']}]({item['link']})")
            lines.append(f"   _{item['source']}_ - {item['summary']}")
        lines.append("")
    return "\n".join(lines).strip()


def build_email_html(new_items, date_str, site_url):
    grouped = group_by_category(new_items)
    parts = [f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;max-width:640px;margin:auto;">
    <h2 style="color:#1a5276;">Gujarat &amp; India Labour Law Digest</h2>
    <p style="color:#666;">{date_str}</p>
    """]
    for category, items in grouped.items():
        parts.append(f'<h3 style="color:#154360;border-bottom:1px solid #ccc;padding-bottom:4px;">{html.escape(category)}</h3>')
        for item in items:
            parts.append(f"""
            <div style="margin-bottom:16px;">
              <a href="{item['link']}" style="font-weight:bold;color:#1a5276;text-decoration:none;">{html.escape(item['title'])}</a>
              <div style="font-size:12px;color:#888;">{html.escape(item['source'])}</div>
              <div style="font-size:14px;margin-top:4px;">{html.escape(item['summary'])}</div>
            </div>
            """)
    if site_url:
        parts.append(f'<p style="margin-top:24px;"><a href="{site_url}">View the full searchable archive &rarr;</a></p>')
    parts.append("</body></html>")
    return "".join(parts)


def build_email_plain(new_items, date_str):
    grouped = group_by_category(new_items)
    lines = [f"Gujarat & India Labour Law Digest - {date_str}", ""]
    for category, items in grouped.items():
        lines.append(f"== {category} ==")
        for item in items:
            lines.append(f"- {item['title']} ({item['source']})")
            lines.append(f"  {item['summary']}")
            lines.append(f"  {item['link']}")
        lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------
# Static site
# ----------------------------------------------------------------

def category_palette(category):
    """Deterministic pastel color pair for a category tag, based on its name."""
    palette = [
        ("#e8f0fe", "#1a56db"),  # blue
        ("#e6f7f0", "#0e7c4a"),  # green
        ("#fdf0e6", "#b5540c"),  # orange
        ("#f5e9fb", "#7d3ac1"),  # purple
        ("#fdeaea", "#c0392b"),  # red
        ("#e9f7f9", "#0f7e8c"),  # teal
        ("#fff7e0", "#9a7d0a"),  # gold
        ("#eef0fc", "#4550c4"),  # indigo
    ]
    idx = int(hashlib.md5(category.encode("utf-8")).hexdigest(), 16) % len(palette)
    return palette[idx]


def build_site(archive):
    items_sorted = sorted(archive, key=lambda x: x.get("added_date", ""), reverse=True)
    categories = sorted(set(i["category"] for i in items_sorted))
    updated_str = now_ist().strftime("%d %b %Y, %I:%M %p IST")

    cards = []
    for item in items_sorted:
        bg, fg = category_palette(item["category"])
        cards.append(f"""
        <a class="card" href="{item['link']}" target="_blank" rel="noopener"
           data-category="{html.escape(item['category'])}"
           data-search="{html.escape((item['title'] + ' ' + item['summary'] + ' ' + item['source']).lower())}">
          <div class="card-top">
            <span class="tag" style="background:{bg};color:{fg};">{html.escape(item['category'])}</span>
            <span class="date">{html.escape(item['added_date'])}</span>
          </div>
          <div class="title">{html.escape(item['title'])}</div>
          <div class="meta">{html.escape(item['source'])}</div>
          <p class="summary">{html.escape(item['summary'])}</p>
          <div class="read-more">Open source &nearr;</div>
        </a>""")

    filter_buttons = ['<button class="filter-btn active" data-cat="all">All</button>']
    for c in categories:
        filter_buttons.append(f'<button class="filter-btn" data-cat="{html.escape(c)}">{html.escape(c)}</button>')

    if items_sorted:
        grid_content = ''.join(cards)
        empty_state = ""
    else:
        grid_content = ""
        empty_state = """
        <div class="empty-state">
          <div class="empty-icon">\U0001F4ED</div>
          <h3>No articles yet</h3>
          <p>The daily job hasn't found or delivered anything here yet.</p>
          <ul>
            <li>It runs automatically every day at <strong>9:00 AM IST</strong></li>
            <li>To check right now: go to your repo's <strong>Actions</strong> tab and see if "Daily Labour Law Digest" has a green checkmark or a red X</li>
            <li>Never run yet? Click <strong>Run workflow</strong> there, or use "Run now" on the <a href="admin.html">Manage Sources</a> page</li>
          </ul>
        </div>"""

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gujarat & India Labour Law Tracker</title>
<style>
  :root {{
    --navy:#0f2d4a; --blue:#1a5276; --blue-light:#2e86c1;
    --bg:#f6f8fb; --card:#ffffff; --border:#e7ebf0; --text:#1c2733; --muted:#6b7785;
  }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; background:var(--bg); margin:0; color:var(--text); }}

  header {{
    background:linear-gradient(135deg, var(--navy), var(--blue-light));
    color:white; padding:36px 20px 44px; text-align:center;
    position:relative;
  }}
  header h1 {{ margin:0 0 6px; font-size:26px; font-weight:700; letter-spacing:-0.3px; }}
  header p {{ margin:0; opacity:0.88; font-size:14px; }}
  .admin-link {{
    display:inline-flex; align-items:center; gap:4px; margin-top:16px; font-size:13px;
    color:white; background:rgba(255,255,255,0.16); padding:7px 16px; border-radius:20px;
    text-decoration:none; font-weight:600; transition:background 0.15s;
  }}
  .admin-link:hover {{ background:rgba(255,255,255,0.3); }}

  .controls {{
    max-width:920px; margin:-26px auto 0; padding:0 20px; position:relative; z-index:2;
  }}
  .search-wrap {{
    background:var(--card); border-radius:14px; box-shadow:0 6px 20px rgba(15,45,74,0.12);
    padding:16px; border:1px solid var(--border);
  }}
  #search {{
    width:100%; padding:12px 14px; font-size:15px; border:1px solid var(--border);
    border-radius:10px; outline:none; transition:border-color 0.15s;
  }}
  #search:focus {{ border-color:var(--blue-light); }}
  .filters {{ margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; }}
  .filter-btn {{
    background:#f0f3f7; border:1px solid transparent; color:var(--muted); border-radius:18px;
    padding:6px 14px; font-size:13px; cursor:pointer; font-weight:600; transition:all 0.15s;
  }}
  .filter-btn:hover {{ background:#e4e9ef; }}
  .filter-btn.active {{ background:var(--navy); color:white; }}

  .grid {{
    max-width:920px; margin:24px auto 0; padding:0 20px 50px;
    display:grid; gap:16px; grid-template-columns:1fr;
  }}
  @media (min-width:700px) {{ .grid {{ grid-template-columns:1fr 1fr; }} }}

  .card {{
    background:var(--card); border-radius:14px; padding:18px 20px; text-decoration:none; color:inherit;
    border:1px solid var(--border); display:flex; flex-direction:column;
    box-shadow:0 1px 2px rgba(15,45,74,0.04); transition:transform 0.15s, box-shadow 0.15s;
  }}
  .card:hover {{ transform:translateY(-2px); box-shadow:0 10px 24px rgba(15,45,74,0.1); border-color:#d3dce6; }}
  .card-top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
  .tag {{ display:inline-block; font-size:11px; font-weight:700; padding:3px 10px; border-radius:10px; }}
  .date {{ font-size:11.5px; color:var(--muted); }}
  .title {{ font-weight:700; color:var(--navy); font-size:16px; line-height:1.35; margin-bottom:6px; }}
  .meta {{ font-size:12.5px; color:var(--muted); margin-bottom:8px; font-weight:600; }}
  .summary {{ font-size:14px; line-height:1.5; margin:0 0 12px; color:#3a4552; flex-grow:1; }}
  .read-more {{ font-size:12.5px; font-weight:700; color:var(--blue-light); margin-top:auto; }}

  .empty-state {{
    grid-column:1 / -1; text-align:center; background:var(--card); border:1px dashed var(--border);
    border-radius:16px; padding:50px 24px; color:var(--muted);
  }}
  .empty-icon {{ font-size:40px; margin-bottom:10px; }}
  .empty-state h3 {{ color:var(--navy); margin:0 0 8px; font-size:18px; }}
  .empty-state p {{ margin:0 0 14px; }}
  .empty-state ul {{ text-align:left; max-width:480px; margin:0 auto; padding-left:20px; line-height:1.7; }}
  .empty-state a {{ color:var(--blue-light); font-weight:600; }}

  footer {{ text-align:center; font-size:12.5px; color:var(--muted); padding:6px 20px 36px; }}
</style>
</head>
<body>
<header>
  <h1>Gujarat &amp; India Labour Law Tracker</h1>
  <p>PF &middot; ESI &middot; Gujarat Labour Law &middot; Central Labour Codes &mdash; auto-updated daily</p>
  <br>
  <a href="admin.html" class="admin-link">+ Manage Sources</a>
</header>
<div class="controls">
  <div class="search-wrap">
    <input id="search" type="text" placeholder="Search titles and summaries...">
    <div class="filters">{''.join(filter_buttons)}</div>
  </div>
</div>
<div class="grid" id="grid">
{grid_content}{empty_state}
</div>
<footer>Last updated {updated_str} &middot; {len(items_sorted)} item{'s' if len(items_sorted) != 1 else ''} archived</footer>
<script>
  const search = document.getElementById('search');
  const buttons = document.querySelectorAll('.filter-btn');
  let activeCat = 'all';

  function applyFilters() {{
    const q = search.value.toLowerCase();
    document.querySelectorAll('.card').forEach(card => {{
      const matchesCat = activeCat === 'all' || card.dataset.category === activeCat;
      const matchesSearch = card.dataset.search.includes(q);
      card.style.display = (matchesCat && matchesSearch) ? '' : 'none';
    }});
  }}

  buttons.forEach(btn => btn.addEventListener('click', () => {{
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeCat = btn.dataset.cat;
    applyFilters();
  }}));

  search.addEventListener('input', applyFilters);
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(SITE_PATH), exist_ok=True)
    with open(SITE_PATH, "w", encoding="utf-8") as f:
        f.write(html_doc)


# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------

def main():
    config = load_config()
    archive = load_archive()
    sources = load_sources()
    existing_links = {item["link"] for item in archive}

    log(f"Fetching sources ({len(sources)} added via website, plus config.yaml defaults)...")
    fetched = collect_all_entries(config, sources)
    log(f"Fetched {len(fetched)} raw entries.")

    new_items = []
    today_str = now_ist().strftime("%Y-%m-%d")
    seen_this_run = set()

    for entry in fetched:
        link = entry["link"]
        if link in existing_links or link in seen_this_run:
            continue
        seen_this_run.add(link)
        summary = summarize(entry, config.get("fallback_summary_length", 400))
        item = {
            "id": make_id(link),
            "title": entry["title"] or "Untitled",
            "link": link,
            "source": entry["source"] or "Unknown source",
            "category": entry["category"],
            "summary": summary,
            "added_date": today_str,
            "notified": False,
        }
        new_items.append(item)
        archive.append(item)

    log(f"Found {len(new_items)} new items.")

    if new_items:
        date_str = now_ist().strftime("%d %b %Y")
        telegram_text = build_telegram_text(new_items, date_str)
        telegram_ok = send_telegram(chunk_text(telegram_text))

        site_url = os.environ.get("SITE_URL", "")
        email_html = build_email_html(new_items, date_str, site_url)
        email_plain = build_email_plain(new_items, date_str)
        email_ok = send_email(
            subject=f"Labour Law Digest - {date_str} ({len(new_items)} new)",
            html_body=email_html,
            plain_body=email_plain,
        )

        if telegram_ok or email_ok:
            for item in new_items:
                item["notified"] = True
        log(f"Telegram sent: {telegram_ok} | Email sent: {email_ok}")
    else:
        log("Nothing new today - no notification sent.")

    # Trim archive to configured max size (keep most recent)
    max_items = config.get("max_archive_items", 800)
    if len(archive) > max_items:
        archive = sorted(archive, key=lambda x: x.get("added_date", ""), reverse=True)[:max_items]

    save_archive(archive)
    build_site(archive)
    log("Archive saved and site rebuilt.")


if __name__ == "__main__":
    sys.exit(main())
