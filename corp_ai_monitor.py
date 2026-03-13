import feedparser
import requests
import time
import os
import json
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
# ============================================================

CHECK_INTERVAL = 1800  # 30 minutes

# ============================================================
# GLOBAL CORPORATE NEWS SOURCES
# Covers USA, Europe, Asia, India, Middle East, Africa
# ============================================================
CORPORATE_SOURCES = [
    # USA
    {"name": "Reuters Business",     "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "WSJ Business",         "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"},
    {"name": "Bloomberg Markets",    "url": "https://feeds.bloomberg.com/markets/news.rss"},
    {"name": "Forbes Business",      "url": "https://www.forbes.com/business/feed/"},
    {"name": "Business Insider",     "url": "https://feeds.businessinsider.com/custom/all"},
    {"name": "TechCrunch",           "url": "https://techcrunch.com/feed/"},
    {"name": "Crunchbase News",      "url": "https://news.crunchbase.com/feed/"},
    {"name": "Layoffs FYI",          "url": "https://layoffs.fyi/feed/"},
    {"name": "CNBC Business",        "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
    {"name": "Fortune",              "url": "https://fortune.com/feed/"},
    {"name": "Fast Company",         "url": "https://www.fastcompany.com/rss"},
    {"name": "Inc Magazine",         "url": "https://www.inc.com/rss"},
    {"name": "Harvard Biz Review",   "url": "https://hbr.org/feed"},
    # EUROPE
    {"name": "Financial Times",      "url": "https://www.ft.com/rss/home"},
    {"name": "The Economist",        "url": "https://www.economist.com/business/rss.xml"},
    {"name": "Guardian Business",    "url": "https://www.theguardian.com/uk/business/rss"},
    {"name": "BBC Business",         "url": "http://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "Deutsche Welle Biz",   "url": "https://rss.dw.com/rdf/rss-en-bus"},
    {"name": "Euronews Business",    "url": "https://www.euronews.com/rss?level=theme&name=business"},
    # ASIA
    {"name": "Nikkei Asia",          "url": "https://asia.nikkei.com/rss/feed/nar"},
    {"name": "South China Morning",  "url": "https://www.scmp.com/rss/92/feed"},
    {"name": "Asia Times Business",  "url": "https://asiatimes.com/category/business/feed/"},
    # INDIA
    {"name": "Economic Times",       "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "Moneycontrol",         "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"name": "Business Standard",    "url": "https://www.business-standard.com/rss/home_page_top_stories.rss"},
    {"name": "Livemint",             "url": "https://www.livemint.com/rss/news"},
    {"name": "Hindu Business",       "url": "https://www.thehindubusinessline.com/feeder/default.rss"},
    {"name": "Inc42 India",          "url": "https://inc42.com/feed/"},
    {"name": "YourStory",            "url": "https://yourstory.com/feed"},
    # MIDDLE EAST
    {"name": "Arabian Business",     "url": "https://www.arabianbusiness.com/rss"},
    {"name": "Gulf News Business",   "url": "https://gulfnews.com/rss/business"},
    # AFRICA
    {"name": "Business Day Africa",  "url": "https://businessday.ng/feed/"},
    {"name": "African Business",     "url": "https://african.business/feed"},
    # LATAM
    {"name": "Latin Finance",        "url": "https://latinfinance.com/feed/"},
]

# ============================================================
# GLOBAL AI NEWS SOURCES
# ============================================================
AI_SOURCES = [
    {"name": "OpenAI Blog",          "url": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic Blog",       "url": "https://www.anthropic.com/rss.xml"},
    {"name": "Google AI Blog",       "url": "https://blog.research.google/atom.xml"},
    {"name": "Meta AI Blog",         "url": "https://ai.meta.com/blog/rss/"},
    {"name": "Microsoft AI Blog",    "url": "https://blogs.microsoft.com/ai/feed/"},
    {"name": "MIT Tech Review AI",   "url": "https://www.technologyreview.com/feed/"},
    {"name": "The Verge AI",         "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "Wired AI",             "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "VentureBeat AI",       "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "ArXiv AI",             "url": "https://arxiv.org/rss/cs.AI"},
    {"name": "Hugging Face Blog",    "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "DeepMind Blog",        "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "AI News",              "url": "https://artificialintelligence-news.com/feed/"},
    {"name": "Synced AI",            "url": "https://syncedreview.com/feed/"},
    {"name": "ImportAI",             "url": "https://importai.substack.com/feed"},
    {"name": "NVIDIA Blog",          "url": "https://blogs.nvidia.com/feed/"},
]

# ============================================================
# CORPORATE KEYWORDS — what to flag
# ============================================================
CORPORATE_KEYWORDS = [
    # Layoffs
    "layoff", "layoffs", "laid off", "job cuts", "retrenchment",
    "redundancies", "workforce reduction", "downsizing", "firing",
    # Hiring
    "hiring", "recruitment", "new jobs", "expanding workforce",
    "headcount", "talent acquisition",
    # Deals
    "acquisition", "merger", "acquires", "buys", "takeover",
    "partnership", "joint venture", "deal worth", "billion deal",
    # Performance
    "earnings", "revenue", "profit", "loss", "quarterly results",
    "beats estimates", "misses estimates", "guidance", "forecast",
    # Leadership
    "ceo", "cfo", "cto", "resigns", "appointed", "steps down",
    "new chief", "leadership change", "board",
    # Debt & Finance
    "debt", "bankruptcy", "chapter 11", "loan", "bond", "credit rating",
    "downgrade", "default", "fundraising", "ipo", "valuation",
    # Growth
    "expansion", "new market", "launches in", "opens office",
    "new product", "revenue growth", "market share",
    # Tech
    "patent", "innovation", "new technology", "ai adoption",
    "digital transformation", "cloud", "automation",
]

# ============================================================
# AI KEYWORDS — what to flag
# ============================================================
AI_KEYWORDS = [
    "gpt", "claude", "gemini", "llm", "large language model",
    "artificial intelligence", "machine learning", "deep learning",
    "ai model", "new model", "benchmark", "beats", "surpasses",
    "openai", "anthropic", "google deepmind", "meta ai", "mistral",
    "funding", "raises", "valuation", "billion", "investment",
    "regulation", "ban", "law", "policy", "safety",
    "open source", "release", "launch", "available",
    "nvidia", "gpu", "chip", "semiconductor",
    "agent", "autonomous", "robotics", "humanoid",
    "copyright", "lawsuit", "legal",
    "agi", "superintelligence", "alignment",
]

# Track already seen articles
seen_articles = set()

def send_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        else:
            print(f"Telegram error: {r.status_code} {r.text}")
            return False
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def analyze_with_claude(headline, source, category):
    """Use Claude to analyze the news and generate ready-to-post content"""
    if not ANTHROPIC_API_KEY:
        return None

    if category == "CORPORATE":
        prompt = f"""You are a sharp corporate intelligence analyst. Analyze this news headline and provide:

Headline: {headline}
Source: {source}

Respond in this EXACT format with no extra text:

MARKET_IMPACT: [2 sentences on market/business impact]
HIDDEN_ANGLE: [1 sentence on what most people are missing]
JOBS_IMPACT: [1 sentence on hiring/layoff implications]
X_POST: [viral tweet under 260 chars that connects this to a bigger pattern, no hashtags]
LINKEDIN_POST: [3-4 sentences professional insight suitable for LinkedIn executives]"""

    else:  # AI
        prompt = f"""You are a sharp AI industry analyst. Analyze this AI news headline and provide:

Headline: {headline}
Source: {source}

Respond in this EXACT format with no extra text:

MARKET_IMPACT: [2 sentences on which companies/stocks are affected]
HIDDEN_ANGLE: [1 sentence on what most people are missing about this]
INDUSTRY_SHIFT: [1 sentence on what this means for the AI industry long term]
X_POST: [viral tweet under 260 chars connecting this to the bigger AI race, no hashtags]
LINKEDIN_POST: [3-4 sentences professional insight suitable for LinkedIn tech leaders]"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data["content"][0]["text"]
        return None
    except Exception as e:
        print(f"Claude API error: {e}")
        return None

def parse_claude_response(text, category):
    """Parse Claude's structured response"""
    if not text:
        return {}

    result = {}
    lines = text.strip().split("\n")

    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()

    return result

def format_corporate_alert(headline, source, url, analysis):
    """Format corporate alert message"""
    now = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")

    msg = f"""🏢 *CORPORATE MONITOR ALERT*
━━━━━━━━━━━━━━━━━━━━
🕐 {now}
📰 *{headline[:200]}*
📡 Source: {source}

"""
    if analysis:
        if "MARKET_IMPACT" in analysis:
            msg += f"📈 *MARKET IMPACT:*\n{analysis.get('MARKET_IMPACT', '')}\n\n"
        if "JOBS_IMPACT" in analysis:
            msg += f"💼 *JOBS IMPACT:*\n{analysis.get('JOBS_IMPACT', '')}\n\n"
        if "HIDDEN_ANGLE" in analysis:
            msg += f"🔍 *HIDDEN ANGLE:*\n{analysis.get('HIDDEN_ANGLE', '')}\n\n"
        if "X_POST" in analysis:
            msg += f"🐦 *POST ON X:*\n_{analysis.get('X_POST', '')}_\n\n"
        if "LINKEDIN_POST" in analysis:
            msg += f"💼 *POST ON LINKEDIN:*\n_{analysis.get('LINKEDIN_POST', '')}_\n\n"

    msg += f"🔗 [Read Full Story]({url})"
    return msg

def format_ai_alert(headline, source, url, analysis):
    """Format AI monitor alert message"""
    now = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")

    msg = f"""🤖 *AI MONITOR ALERT*
━━━━━━━━━━━━━━━━━━━━
🕐 {now}
📰 *{headline[:200]}*
📡 Source: {source}

"""
    if analysis:
        if "MARKET_IMPACT" in analysis:
            msg += f"📈 *MARKET IMPACT:*\n{analysis.get('MARKET_IMPACT', '')}\n\n"
        if "INDUSTRY_SHIFT" in analysis:
            msg += f"🔄 *INDUSTRY SHIFT:*\n{analysis.get('INDUSTRY_SHIFT', '')}\n\n"
        if "HIDDEN_ANGLE" in analysis:
            msg += f"🔍 *HIDDEN ANGLE:*\n{analysis.get('HIDDEN_ANGLE', '')}\n\n"
        if "X_POST" in analysis:
            msg += f"🐦 *POST ON X:*\n_{analysis.get('X_POST', '')}_\n\n"
        if "LINKEDIN_POST" in analysis:
            msg += f"💼 *POST ON LINKEDIN:*\n_{analysis.get('LINKEDIN_POST', '')}_\n\n"

    msg += f"🔗 [Read Full Story]({url})"
    return msg

def is_relevant(title, keywords):
    """Check if headline matches our keywords"""
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in keywords)

def get_article_id(title, link):
    """Generate unique ID for article"""
    return str(hash(title[:50] + link[:50]))

def scan_sources(sources, keywords, category):
    """Scan RSS sources and send alerts"""
    alerts_sent = 0

    for source in sources:
        try:
            feed = feedparser.parse(source["url"])
            entries = feed.entries[:10]  # check latest 10 per source

            for entry in entries:
                title = entry.get("title", "")
                link  = entry.get("link", "")

                if not title or not link:
                    continue

                # Skip if already seen
                article_id = get_article_id(title, link)
                if article_id in seen_articles:
                    continue

                # Check if relevant
                if not is_relevant(title, keywords):
                    seen_articles.add(article_id)
                    continue

                print(f"[{category}] Relevant: {title[:80]}...")

                # Analyze with Claude
                raw_analysis = analyze_with_claude(title, source["name"], category)
                analysis = parse_claude_response(raw_analysis, category)

                # Format and send
                if category == "CORPORATE":
                    message = format_corporate_alert(title, source["name"], link, analysis)
                else:
                    message = format_ai_alert(title, source["name"], link, analysis)

                if send_telegram(message):
                    alerts_sent += 1
                    print(f"Alert sent for: {title[:60]}")
                    time.sleep(5)  # avoid spam

                seen_articles.add(article_id)

                # Keep seen set manageable
                if len(seen_articles) > 5000:
                    seen_articles.clear()

        except Exception as e:
            print(f"Error scanning {source['name']}: {e}")
            continue

    return alerts_sent

def main():
    print("=" * 60)
    print("Corporate + AI Monitor Bot Started")
    print(f"Corporate sources: {len(CORPORATE_SOURCES)}")
    print(f"AI sources: {len(AI_SOURCES)}")
    print(f"Checking every {CHECK_INTERVAL//60} minutes")
    print("=" * 60)

    send_telegram(f"""🚀 *Corporate + AI Monitor Bot ONLINE*
━━━━━━━━━━━━━━━━━━━━
*Tracking globally every 30 minutes:*

🏢 *CORPORATE MONITOR*
✅ {len(CORPORATE_SOURCES)} global sources
✅ USA, Europe, Asia, India, Middle East, Africa
✅ Layoffs, Hiring, Deals, Earnings
✅ Leadership changes, Debt, IPOs
✅ Ready-to-post X + LinkedIn content

🤖 *AI MONITOR*
✅ {len(AI_SOURCES)} AI sources
✅ New models, Funding, Research
✅ Regulation, Open source releases
✅ Chip & GPU news
✅ Ready-to-post X + LinkedIn content

━━━━━━━━━━━━━━━━━━━━
Every alert includes:
📈 Market impact analysis
🔍 Hidden angle others miss
🐦 Ready viral X post
💼 Ready LinkedIn post
🔗 Full story link

⚡ _Your unfair advantage starts now_""")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting scan...")

        # Scan corporate sources
        print("Scanning corporate sources...")
        corp_alerts = scan_sources(CORPORATE_SOURCES, CORPORATE_KEYWORDS, "CORPORATE")
        print(f"Corporate alerts sent: {corp_alerts}")

        # Small gap between scans
        time.sleep(10)

        # Scan AI sources
        print("Scanning AI sources...")
        ai_alerts = scan_sources(AI_SOURCES, AI_KEYWORDS, "AI")
        print(f"AI alerts sent: {ai_alerts}")

        print(f"Scan complete. Total alerts: {corp_alerts + ai_alerts}")
        print(f"Sleeping {CHECK_INTERVAL//60} minutes until next scan...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
