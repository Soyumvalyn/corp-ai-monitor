import feedparser
import requests
import time
import os
from datetime import datetime, timezone
import email.utils

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY")

CHECK_INTERVAL = 1800
MAX_AGE_HOURS  = 12

CORPORATE_SOURCES = [
    {"name": "Reuters Business",    "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "BBC Business",        "url": "http://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "CNBC Business",       "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
    {"name": "Forbes Business",     "url": "https://www.forbes.com/business/feed/"},
    {"name": "TechCrunch",          "url": "https://techcrunch.com/feed/"},
    {"name": "Financial Times",     "url": "https://www.ft.com/rss/home"},
    {"name": "Economic Times",      "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "Moneycontrol",        "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"name": "Business Standard",   "url": "https://www.business-standard.com/rss/home_page_top_stories.rss"},
    {"name": "Crunchbase News",     "url": "https://news.crunchbase.com/feed/"},
    {"name": "Layoffs FYI",         "url": "https://layoffs.fyi/feed/"},
    {"name": "Guardian Business",   "url": "https://www.theguardian.com/uk/business/rss"},
    {"name": "South China Morning", "url": "https://www.scmp.com/rss/92/feed"},
    {"name": "Arabian Business",    "url": "https://www.arabianbusiness.com/rss"},
]

AI_SOURCES = [
    {"name": "TechCrunch AI",       "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge AI",        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "VentureBeat AI",      "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "MIT Tech Review",     "url": "https://www.technologyreview.com/feed/"},
    {"name": "Wired AI",            "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "NVIDIA Blog",         "url": "https://blogs.nvidia.com/feed/"},
    {"name": "Hugging Face",        "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "DeepMind Blog",       "url": "https://deepmind.google/blog/rss.xml"},
]

CORPORATE_KEYWORDS = [
    "layoff","layoffs","laid off","job cuts","firing","redundan",
    "hiring","recruitment","new jobs",
    "acquisition","merger","acquires","takeover","deal worth",
    "earnings","revenue","profit","loss","quarterly",
    "beats estimates","misses estimates",
    "ceo","cfo","resigns","appointed","steps down",
    "bankruptcy","credit rating","downgrade","ipo","fundraising",
    "expansion","new market","launches",
]

AI_KEYWORDS = [
    "gpt","claude","gemini","llm","large language model",
    "artificial intelligence","machine learning",
    "ai model","new model","benchmark",
    "openai","anthropic","deepmind","meta ai","mistral",
    "funding","raises","billion",
    "regulation","ban","safety",
    "open source","release","launch",
    "nvidia","gpu","chip",
    "agent","autonomous","robotics","agi",
]

seen = set()

def send_telegram(text):
    if len(text) > 4000:
        text = text[:4000] + "...[truncated]"
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                  "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print(f"Telegram error: {e}")

def get_age_hours(entry):
    try:
        for attr in ["published_parsed", "updated_parsed"]:
            val = getattr(entry, attr, None)
            if val:
                t = datetime(*val[:6], tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - t).total_seconds() / 3600
        if hasattr(entry, "published") and entry.published:
            t = email.utils.parsedate_to_datetime(entry.published)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except:
        pass
    return 999

def analyze(headline, source, category):
    if not GROQ_API_KEY:
        return None

    if category == "CORPORATE":
        prompt = f"""Analyze this corporate news for a finance audience.
Headline: {headline}
Source: {source}

Reply in EXACTLY this format, nothing else:
MARKET_IMPACT: [2 sentences on business impact]
JOBS_IMPACT: [1 sentence on hiring/layoff implications]
HIDDEN_ANGLE: [1 sentence most analysts miss]
X_POST: [punchy tweet under 260 chars, no hashtags, make people stop scrolling]
LINKEDIN_POST: [3 sentences for executives and investors]"""
    else:
        prompt = f"""Analyze this AI news for a tech and finance audience.
Headline: {headline}
Source: {source}

Reply in EXACTLY this format, nothing else:
MARKET_IMPACT: [2 sentences on which companies are affected]
INDUSTRY_SHIFT: [1 sentence on long term AI industry impact]
HIDDEN_ANGLE: [1 sentence most people miss]
X_POST: [punchy tweet under 260 chars, no hashtags, connect to bigger AI race]
LINKEDIN_POST: [3 sentences for tech leaders and investors]"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            print(f"Groq error {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Groq exception: {e}")
        return None

def parse(text):
    result = {}
    if not text:
        return result
    for line in text.strip().split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                result[k] = v
    return result

def format_msg(headline, source, url, analysis, category, age):
    now = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
    age_str = f"{int(age*60)}m ago" if age < 1 else f"{age:.1f}h ago"
    header = "🏢 *CORPORATE MONITOR*" if category == "CORPORATE" else "🤖 *AI MONITOR*"

    msg = f"{header}\n━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🕐 {now} _({age_str})_\n"
    msg += f"📰 *{headline[:180]}*\n"
    msg += f"📡 _{source}_\n\n"

    if analysis:
        for key, emoji, label in [
            ("MARKET_IMPACT",  "📈", "MARKET IMPACT"),
            ("JOBS_IMPACT",    "💼", "JOBS IMPACT"),
            ("INDUSTRY_SHIFT", "🔄", "INDUSTRY SHIFT"),
            ("HIDDEN_ANGLE",   "🔍", "HIDDEN ANGLE"),
        ]:
            if key in analysis:
                msg += f"{emoji} *{label}:*\n{analysis[key]}\n\n"

        if "X_POST" in analysis:
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🐦 *COPY & POST ON X:*\n\n{analysis['X_POST']}\n\n"
        if "LINKEDIN_POST" in analysis:
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"💼 *COPY & POST ON LINKEDIN:*\n\n{analysis['LINKEDIN_POST']}\n\n"
    else:
        msg += "_Analysis unavailable_\n\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━\n🔗 [Read Full Story]({url})"
    return msg

def scan(sources, keywords, category):
    sent = 0
    for src in sources:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "").strip()
                if not title or not link:
                    continue
                uid = str(hash(title[:60]))
                if uid in seen:
                    continue
                seen.add(uid)
                age = get_age_hours(entry)
                if age > MAX_AGE_HOURS:
                    continue
                if not any(k.lower() in title.lower() for k in keywords):
                    continue
                print(f"[{category}] {age:.1f}h: {title[:70]}")
                raw = analyze(title, src["name"], category)
                a   = parse(raw)
                msg = format_msg(title, src["name"], link, a, category, age)
                send_telegram(msg)
                sent += 1
                time.sleep(5)
        except Exception as e:
            print(f"Error {src['name']}: {e}")
    if len(seen) > 5000:
        seen.clear()
    return sent

def main():
    print("Corp + AI Monitor — Groq Edition")
    print(f"Model: llama-3.1-8b-instant (FREE)")
    print(f"Max age: {MAX_AGE_HOURS}h | Interval: {CHECK_INTERVAL//60}min")

    send_telegram("""🚀 *Corp + AI Monitor GROQ Edition ONLINE*
━━━━━━━━━━━━━━━━━━━━
✅ Powered by Groq AI — 100% FREE
✅ Fresh news only (last 12 hours)
✅ Full analysis on every alert
✅ Ready X post + LinkedIn post

Scanning every 30 minutes...
⚡ _Your edge starts now_""")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning...")
        c = scan(CORPORATE_SOURCES, CORPORATE_KEYWORDS, "CORPORATE")
        time.sleep(10)
        a = scan(AI_SOURCES, AI_KEYWORDS, "AI")
        print(f"Done. {c+a} alerts. Sleeping {CHECK_INTERVAL//60}min...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
