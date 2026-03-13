import feedparser
import requests
import time
import os
from datetime import datetime, timezone, timedelta
import email.utils

# ============================================================
# CONFIGURATION
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
# ============================================================

CHECK_INTERVAL = 600       # 10 minutes
MAX_ARTICLE_AGE_HOURS = 12   # Only show articles from last 12 hours

# ============================================================
# GLOBAL CORPORATE NEWS SOURCES
# ============================================================
CORPORATE_SOURCES = [
    {"name": "Reuters Business",     "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "WSJ Business",         "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"},
    {"name": "Forbes Business",      "url": "https://www.forbes.com/business/feed/"},
    {"name": "Business Insider",     "url": "https://feeds.businessinsider.com/custom/all"},
    {"name": "TechCrunch",           "url": "https://techcrunch.com/feed/"},
    {"name": "Crunchbase News",      "url": "https://news.crunchbase.com/feed/"},
    {"name": "Layoffs FYI",          "url": "https://layoffs.fyi/feed/"},
    {"name": "CNBC Business",        "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
    {"name": "Fortune",              "url": "https://fortune.com/feed/"},
    {"name": "Financial Times",      "url": "https://www.ft.com/rss/home"},
    {"name": "BBC Business",         "url": "http://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "Guardian Business",    "url": "https://www.theguardian.com/uk/business/rss"},
    {"name": "Nikkei Asia",          "url": "https://asia.nikkei.com/rss/feed/nar"},
    {"name": "Economic Times",       "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "Moneycontrol",         "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"name": "Business Standard",    "url": "https://www.business-standard.com/rss/home_page_top_stories.rss"},
    {"name": "Livemint",             "url": "https://www.livemint.com/rss/news"},
    {"name": "Inc42 India",          "url": "https://inc42.com/feed/"},
    {"name": "Arabian Business",     "url": "https://www.arabianbusiness.com/rss"},
    {"name": "Gulf News Business",   "url": "https://gulfnews.com/rss/business"},
    {"name": "South China Morning",  "url": "https://www.scmp.com/rss/92/feed"},
]

# ============================================================
# AI NEWS SOURCES
# ============================================================
AI_SOURCES = [
    {"name": "OpenAI Blog",          "url": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic Blog",       "url": "https://www.anthropic.com/rss.xml"},
    {"name": "Google DeepMind",      "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Meta AI Blog",         "url": "https://ai.meta.com/blog/rss/"},
    {"name": "Microsoft AI",         "url": "https://blogs.microsoft.com/ai/feed/"},
    {"name": "MIT Tech Review",      "url": "https://www.technologyreview.com/feed/"},
    {"name": "The Verge AI",         "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "Wired AI",             "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "VentureBeat AI",       "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Hugging Face Blog",    "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "NVIDIA Blog",          "url": "https://blogs.nvidia.com/feed/"},
    {"name": "TechCrunch AI",        "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
]

# ============================================================
# KEYWORDS
# ============================================================
CORPORATE_KEYWORDS = [
    "layoff", "layoffs", "laid off", "job cuts", "retrenchment",
    "hiring", "recruitment", "new jobs",
    "acquisition", "merger", "acquires", "buys", "takeover",
    "partnership", "joint venture", "deal worth",
    "earnings", "revenue", "profit", "loss", "quarterly results",
    "beats estimates", "misses estimates",
    "ceo", "cfo", "cto", "resigns", "appointed", "steps down",
    "bankruptcy", "chapter 11", "credit rating", "downgrade",
    "ipo", "valuation", "fundraising", "raises",
    "expansion", "new market", "launches",
]

AI_KEYWORDS = [
    "gpt", "claude", "gemini", "llm", "large language model",
    "artificial intelligence", "machine learning",
    "ai model", "new model", "benchmark",
    "openai", "anthropic", "deepmind", "meta ai", "mistral",
    "funding", "raises", "billion",
    "regulation", "ban", "law", "safety",
    "open source", "release", "launch",
    "nvidia", "gpu", "chip",
    "agent", "autonomous", "robotics",
    "agi", "superintelligence",
]

# Track seen articles
seen_articles = set()

def send_telegram(message):
    """Send message to Telegram — split if too long"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Telegram max is 4096 chars
    if len(message) > 4000:
        message = message[:4000] + "...\n\n[Message truncated]"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def get_article_age_hours(entry):
    """Get article age in hours — returns 999 if can't parse"""
    try:
        # Try published_parsed first
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
            return age

        # Try published string
        if hasattr(entry, 'published') and entry.published:
            pub_time = email.utils.parsedate_to_datetime(entry.published)
            if pub_time.tzinfo is None:
                pub_time = pub_time.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
            return age

        # Try updated
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            pub_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
            return age

    except Exception as e:
        print(f"Date parse error: {e}")

    return 999  # Unknown age — skip it

def analyze_with_claude(headline, source, url, category):
    """Use Claude to analyze and generate ready-to-post content"""
    if not ANTHROPIC_API_KEY:
        return None

    if category == "CORPORATE":
        prompt = f"""You are a sharp corporate intelligence analyst writing for a finance and business audience on X (Twitter) and LinkedIn.

Analyze this news:
Headline: {headline}
Source: {source}

Give me EXACTLY this format — no extra text, no preamble:

MARKET_IMPACT: [2 sharp sentences on business/market impact]
JOBS_IMPACT: [1 sentence on hiring or layoff implications]  
HIDDEN_ANGLE: [1 sentence on what most analysts are missing]
X_POST: [A punchy viral tweet under 260 chars. No hashtags. Connect to a bigger pattern. Make people stop scrolling.]
LINKEDIN_POST: [3-4 sentences of sharp professional insight. Suitable for executives and investors. No fluff.]"""

    else:
        prompt = f"""You are a sharp AI industry analyst writing for a tech and finance audience on X (Twitter) and LinkedIn.

Analyze this AI news:
Headline: {headline}
Source: {source}

Give me EXACTLY this format — no extra text, no preamble:

MARKET_IMPACT: [2 sharp sentences on which companies or stocks are affected]
INDUSTRY_SHIFT: [1 sentence on what this means for the AI industry long term]
HIDDEN_ANGLE: [1 sentence on what most people are missing about this]
X_POST: [A punchy viral tweet under 260 chars. No hashtags. Connect to the bigger AI race. Make people stop scrolling.]
LINKEDIN_POST: [3-4 sentences of sharp professional insight for tech leaders and investors. No fluff.]"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data["content"][0]["text"]
        else:
            print(f"Claude API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Claude error: {e}")
        return None

def parse_analysis(text):
    """Parse Claude's structured response into dict"""
    if not text:
        return {}
    result = {}
    for line in text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key and value:
                result[key] = value
    return result

def format_alert(headline, source, url, analysis, category, age_hours):
    """Format the complete Telegram alert"""
    now = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")

    if age_hours < 1:
        age_str = f"{int(age_hours * 60)} mins ago"
    else:
        age_str = f"{age_hours:.1f} hrs ago"

    if category == "CORPORATE":
        header = "🏢 *CORPORATE MONITOR*"
    else:
        header = "🤖 *AI MONITOR*"

    msg = f"""{header}
━━━━━━━━━━━━━━━━━━━━
🕐 {now} _(published {age_str})_
📰 *{headline[:180]}*
📡 _{source}_

"""
    if analysis:
        if "MARKET_IMPACT" in analysis:
            msg += f"📈 *MARKET IMPACT:*\n{analysis['MARKET_IMPACT']}\n\n"

        if "JOBS_IMPACT" in analysis:
            msg += f"💼 *JOBS IMPACT:*\n{analysis['JOBS_IMPACT']}\n\n"

        if "INDUSTRY_SHIFT" in analysis:
            msg += f"🔄 *INDUSTRY SHIFT:*\n{analysis['INDUSTRY_SHIFT']}\n\n"

        if "HIDDEN_ANGLE" in analysis:
            msg += f"🔍 *HIDDEN ANGLE:*\n{analysis['HIDDEN_ANGLE']}\n\n"

        if "X_POST" in analysis:
            msg += f"━━━━━━━━━━━━━━━━━━━━\n🐦 *COPY & POST ON X:*\n\n{analysis['X_POST']}\n\n"

        if "LINKEDIN_POST" in analysis:
            msg += f"━━━━━━━━━━━━━━━━━━━━\n💼 *COPY & POST ON LINKEDIN:*\n\n{analysis['LINKEDIN_POST']}\n\n"
    else:
        msg += "_Analysis unavailable — check Anthropic API key_\n\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━\n🔗 [Read Full Story]({url})"
    return msg

def is_relevant(title, keywords):
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)

def scan_sources(sources, keywords, category):
    alerts_sent = 0

    for source in sources:
        try:
            feed = feedparser.parse(source["url"])
            entries = feed.entries[:15]

            for entry in entries:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "").strip()

                if not title or not link:
                    continue

                # Skip seen articles
                article_id = str(hash(title[:60]))
                if article_id in seen_articles:
                    continue

                seen_articles.add(article_id)

                # Check article age — ONLY last 6 hours
                age_hours = get_article_age_hours(entry)
                if age_hours > MAX_ARTICLE_AGE_HOURS:
                    continue

                # Check relevance
                if not is_relevant(title, keywords):
                    continue

                print(f"[{category}] ✅ Fresh article ({age_hours:.1f}h): {title[:70]}")

                # Get Claude analysis
                raw = analyze_with_claude(title, source["name"], link, category)
                analysis = parse_analysis(raw)

                # Format and send
                message = format_alert(title, source["name"], link, analysis, category, age_hours)

                if send_telegram(message):
                    alerts_sent += 1
                    print(f"Alert sent!")
                    time.sleep(5)

        except Exception as e:
            print(f"Error scanning {source['name']}: {e}")
            continue

        # Keep seen set manageable
        if len(seen_articles) > 5000:
            seen_articles.clear()

    return alerts_sent

def main():
    print("=" * 60)
    print("Corporate + AI Monitor Bot v2 Started")
    print(f"Only showing articles from last {MAX_ARTICLE_AGE_HOURS} hours")
    print(f"Checking every {CHECK_INTERVAL // 60} minutes")
    print("=" * 60)

    send_telegram(f"""🚀 *Corporate + AI Monitor Bot v2 ONLINE*
━━━━━━━━━━━━━━━━━━━━
✅ Fixed: Only fresh news (last 6 hours)
✅ Fixed: Full AI analysis on every alert
✅ Fixed: Ready-to-post X and LinkedIn content

*Tracking globally every 30 minutes:*
🏢 {len(CORPORATE_SOURCES)} corporate sources worldwide
🤖 {len(AI_SOURCES)} AI sources worldwide

*Every alert now includes:*
📈 Market impact
💼 Jobs impact  
🔍 Hidden angle
🐦 Copy-paste ready X post
💼 Copy-paste ready LinkedIn post

━━━━━━━━━━━━━━━━━━━━
⚡ _Your unfair advantage starts now_""")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning...")

        corp_alerts = scan_sources(CORPORATE_SOURCES, CORPORATE_KEYWORDS, "CORPORATE")
        time.sleep(10)
        ai_alerts = scan_sources(AI_SOURCES, AI_KEYWORDS, "AI")

        total = corp_alerts + ai_alerts
        print(f"Scan done. {total} alerts sent. Sleeping {CHECK_INTERVAL // 60} mins...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
