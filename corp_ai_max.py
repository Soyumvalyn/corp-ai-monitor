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

# ============================================================
# 100 FASTEST CORPORATE NEWS SOURCES — GLOBAL
# ============================================================
CORPORATE_SOURCES = [
    # ── USA TIER 1 (Fastest breaking business news) ──
    {"name": "Reuters Business",       "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "Reuters Top News",       "url": "https://feeds.reuters.com/reuters/topNews"},
    {"name": "AP Business",            "url": "https://rsshub.app/apnews/topics/business"},
    {"name": "CNBC Business",          "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
    {"name": "CNBC Finance",           "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html"},
    {"name": "CNBC Technology",        "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html"},
    {"name": "WSJ Business",           "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"},
    {"name": "WSJ Markets",            "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
    {"name": "Bloomberg Markets",      "url": "https://feeds.bloomberg.com/markets/news.rss"},
    {"name": "Bloomberg Technology",   "url": "https://feeds.bloomberg.com/technology/news.rss"},
    {"name": "Forbes Business",        "url": "https://www.forbes.com/business/feed/"},
    {"name": "Forbes Technology",      "url": "https://www.forbes.com/technology/feed/"},
    {"name": "Fortune",                "url": "https://fortune.com/feed/"},
    {"name": "Business Insider",       "url": "https://feeds.businessinsider.com/custom/all"},
    {"name": "Fast Company",           "url": "https://www.fastcompany.com/rss"},
    {"name": "Inc Magazine",           "url": "https://www.inc.com/rss"},
    {"name": "TechCrunch",             "url": "https://techcrunch.com/feed/"},
    {"name": "TechCrunch Startups",    "url": "https://techcrunch.com/category/startups/feed/"},
    {"name": "Crunchbase News",        "url": "https://news.crunchbase.com/feed/"},
    {"name": "Layoffs FYI",            "url": "https://layoffs.fyi/feed/"},
    {"name": "The Verge Business",     "url": "https://www.theverge.com/business/rss/index.xml"},
    {"name": "Axios Business",         "url": "https://api.axios.com/feed/"},
    {"name": "Quartz",                 "url": "https://qz.com/rss"},
    {"name": "MarketWatch",            "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    {"name": "Investopedia",           "url": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_headline"},
    {"name": "Seeking Alpha",          "url": "https://seekingalpha.com/market_currents.xml"},
    {"name": "Harvard Biz Review",     "url": "https://hbr.org/feed"},
    {"name": "MIT Sloan Review",       "url": "https://sloanreview.mit.edu/feed/"},

    # ── USA TIER 2 (Sector specific) ──
    {"name": "Retail Dive",            "url": "https://www.retaildive.com/feeds/news/"},
    {"name": "Supply Chain Dive",      "url": "https://www.supplychaindive.com/feeds/news/"},
    {"name": "HR Dive",                "url": "https://www.hrdive.com/feeds/news/"},
    {"name": "CFO Dive",               "url": "https://www.cfodive.com/feeds/news/"},
    {"name": "Healthcare Dive",        "url": "https://www.healthcaredive.com/feeds/news/"},
    {"name": "Biopharmadive",          "url": "https://www.biopharmadive.com/feeds/news/"},
    {"name": "Utility Dive",           "url": "https://www.utilitydive.com/feeds/news/"},
    {"name": "Transport Topics",       "url": "https://www.ttnews.com/rss.xml"},
    {"name": "Oil Price",              "url": "https://oilprice.com/rss/main"},
    {"name": "Rigzone",                "url": "https://www.rigzone.com/news/rss/rigzone_latest.aspx"},

    # ── EUROPE ──
    {"name": "Financial Times",        "url": "https://www.ft.com/rss/home"},
    {"name": "The Economist",          "url": "https://www.economist.com/business/rss.xml"},
    {"name": "Guardian Business",      "url": "https://www.theguardian.com/uk/business/rss"},
    {"name": "BBC Business",           "url": "http://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "Sky News Business",      "url": "https://feeds.skynews.com/feeds/rss/business.xml"},
    {"name": "Telegraph Business",     "url": "https://www.telegraph.co.uk/rss.xml"},
    {"name": "Deutsche Welle Biz",     "url": "https://rss.dw.com/rdf/rss-en-bus"},
    {"name": "Euronews Business",      "url": "https://www.euronews.com/rss?level=theme&name=business"},
    {"name": "Les Echos",              "url": "https://www.lesechos.fr/rss/rss_finance.xml"},
    {"name": "Handelsblatt",           "url": "https://www.handelsblatt.com/contentexport/feed/schlagzeilen"},
    {"name": "Il Sole 24 Ore",         "url": "https://www.ilsole24ore.com/rss/economia--finanza.xml"},
    {"name": "El Economista",          "url": "https://www.eleconomista.es/rss/rss-seleccion-ee.php"},
    {"name": "NRC Business",           "url": "https://www.nrc.nl/rss/"},

    # ── ASIA PACIFIC ──
    {"name": "Nikkei Asia",            "url": "https://asia.nikkei.com/rss/feed/nar"},
    {"name": "South China Morning",    "url": "https://www.scmp.com/rss/92/feed"},
    {"name": "Asia Times Business",    "url": "https://asiatimes.com/category/business/feed/"},
    {"name": "Straits Times Business", "url": "https://www.straitstimes.com/business/rss.xml"},
    {"name": "Channel News Asia Biz",  "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6329"},
    {"name": "Australian Financial",   "url": "https://www.afr.com/rss"},
    {"name": "Korea Herald Business",  "url": "http://www.koreaherald.com/rss_xml/all.xml"},
    {"name": "Japan Times Business",   "url": "https://www.japantimes.co.jp/feed/"},

    # ── INDIA (Fastest sources) ──
    {"name": "Economic Times",         "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "ET Markets",             "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"},
    {"name": "ET Tech",                "url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms"},
    {"name": "Moneycontrol Business",  "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"name": "Moneycontrol Markets",   "url": "https://www.moneycontrol.com/rss/marketreports.xml"},
    {"name": "Business Standard",      "url": "https://www.business-standard.com/rss/home_page_top_stories.rss"},
    {"name": "Livemint",               "url": "https://www.livemint.com/rss/news"},
    {"name": "Hindu Business Line",    "url": "https://www.thehindubusinessline.com/feeder/default.rss"},
    {"name": "Financial Express",      "url": "https://www.financialexpress.com/feed/"},
    {"name": "Inc42",                  "url": "https://inc42.com/feed/"},
    {"name": "YourStory",              "url": "https://yourstory.com/feed"},
    {"name": "VCCircle",               "url": "https://www.vccircle.com/feed"},
    {"name": "Entrackr",               "url": "https://entrackr.com/feed/"},
    {"name": "The Ken",                "url": "https://the-ken.com/feed/"},

    # ── MIDDLE EAST ──
    {"name": "Arabian Business",       "url": "https://www.arabianbusiness.com/rss"},
    {"name": "Gulf News Business",     "url": "https://gulfnews.com/rss/business"},
    {"name": "Khaleej Times Business", "url": "https://www.khaleejtimes.com/business/feed"},
    {"name": "MEED",                   "url": "https://www.meed.com/rss"},
    {"name": "Al Monitor Economy",     "url": "https://www.al-monitor.com/rss"},

    # ── AFRICA ──
    {"name": "Business Day Africa",    "url": "https://businessday.ng/feed/"},
    {"name": "African Business",       "url": "https://african.business/feed"},
    {"name": "Daily Maverick Biz",     "url": "https://www.dailymaverick.co.za/opinionista/feed/"},
    {"name": "This Is Africa",         "url": "https://thisisafrica.me/feed/"},

    # ── LATIN AMERICA ──
    {"name": "Latin Finance",          "url": "https://latinfinance.com/feed/"},
    {"name": "BN Americas",            "url": "https://www.bnamericas.com/rss/news"},

    # ── GLOBAL WIRE SERVICES ──
    {"name": "PR Newswire",            "url": "https://www.prnewswire.com/rss/news-releases-list.rss"},
    {"name": "Business Wire",          "url": "https://feed.businesswire.com/rss/home/?rss=G1"},
    {"name": "Globe Newswire",         "url": "https://www.globenewswire.com/RssFeed/subjectcode/50-Mergers%20Acquisitions/industryid/0"},
    {"name": "Seeking Alpha News",     "url": "https://seekingalpha.com/feed.xml"},
    {"name": "Benzinga",               "url": "https://www.benzinga.com/feed"},
    {"name": "Zacks Investment",       "url": "https://www.zacks.com/commentary/rss"},
    {"name": "TheStreet",              "url": "https://www.thestreet.com/rss/main.rss"},
    {"name": "Motley Fool",            "url": "https://www.fool.com/feeds/index.aspx"},
]

# ============================================================
# 50 FASTEST AI NEWS SOURCES — GLOBAL
# ============================================================
AI_SOURCES = [
    # ── OFFICIAL COMPANY BLOGS (Fastest primary sources) ──
    {"name": "OpenAI Blog",            "url": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic Blog",         "url": "https://www.anthropic.com/rss.xml"},
    {"name": "Google DeepMind",        "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Google AI Blog",         "url": "https://blog.research.google/atom.xml"},
    {"name": "Meta AI Blog",           "url": "https://ai.meta.com/blog/rss/"},
    {"name": "Microsoft AI Blog",      "url": "https://blogs.microsoft.com/ai/feed/"},
    {"name": "NVIDIA Blog",            "url": "https://blogs.nvidia.com/feed/"},
    {"name": "Hugging Face Blog",      "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Mistral Blog",           "url": "https://mistral.ai/news/rss"},
    {"name": "Cohere Blog",            "url": "https://cohere.com/blog/rss"},
    {"name": "Scale AI Blog",          "url": "https://scale.com/blog/feed"},
    {"name": "Stability AI Blog",      "url": "https://stability.ai/news/rss"},
    {"name": "Runway Blog",            "url": "https://runwayml.com/blog/rss"},
    {"name": "Perplexity Blog",        "url": "https://blog.perplexity.ai/feed"},
    {"name": "xAI Blog",               "url": "https://x.ai/blog/rss.xml"},

    # ── FAST AI NEWS OUTLETS ──
    {"name": "TechCrunch AI",          "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge AI",           "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "VentureBeat AI",         "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Wired AI",               "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss"},
    {"name": "MIT Tech Review AI",     "url": "https://www.technologyreview.com/feed/"},
    {"name": "Ars Technica AI",        "url": "https://arstechnica.com/feed/"},
    {"name": "ZDNet AI",               "url": "https://www.zdnet.com/topic/artificial-intelligence/rss.xml"},
    {"name": "InfoWorld AI",           "url": "https://www.infoworld.com/category/artificial-intelligence/index.rss"},
    {"name": "AI News",                "url": "https://artificialintelligence-news.com/feed/"},
    {"name": "Synced AI",              "url": "https://syncedreview.com/feed/"},
    {"name": "The Batch",              "url": "https://www.deeplearning.ai/the-batch/feed/"},
    {"name": "Last Week in AI",        "url": "https://lastweekin.ai/feed"},
    {"name": "Import AI",              "url": "https://importai.substack.com/feed"},
    {"name": "AI Alignment Forum",     "url": "https://www.alignmentforum.org/feed.xml"},
    {"name": "Machine Learning Mastery","url": "https://machinelearningmastery.com/feed/"},

    # ── RESEARCH & ACADEMIC ──
    {"name": "ArXiv CS.AI",            "url": "https://arxiv.org/rss/cs.AI"},
    {"name": "ArXiv CS.LG",            "url": "https://arxiv.org/rss/cs.LG"},
    {"name": "ArXiv CS.CL",            "url": "https://arxiv.org/rss/cs.CL"},
    {"name": "Papers With Code",       "url": "https://paperswithcode.com/latest.xml"},
    {"name": "Distill.pub",            "url": "https://distill.pub/rss.xml"},

    # ── BUSINESS OF AI ──
    {"name": "AI Business",            "url": "https://aibusiness.com/rss.xml"},
    {"name": "AI Magazine",            "url": "https://aimagazine.com/rss"},
    {"name": "Forbes AI",              "url": "https://www.forbes.com/ai/feed/"},
    {"name": "CNBC AI",                "url": "https://www.cnbc.com/id/100727362/device/rss/rss.html"},
    {"name": "Reuters AI",             "url": "https://feeds.reuters.com/reuters/technologyNews"},
    {"name": "Bloomberg AI",           "url": "https://feeds.bloomberg.com/technology/news.rss"},
    {"name": "Financial Times Tech",   "url": "https://www.ft.com/technology/rss"},

    # ── CHIPS & HARDWARE ──
    {"name": "AnandTech",              "url": "https://www.anandtech.com/rss/"},
    {"name": "Tom's Hardware",         "url": "https://www.tomshardware.com/feeds/all"},
    {"name": "EE Times",               "url": "https://www.eetimes.com/feed/"},
    {"name": "Semiconductor Engineering","url": "https://semiengineering.com/feed/"},
    {"name": "The Chip Letter",        "url": "https://thechipletter.substack.com/feed"},

    # ── POLICY & REGULATION ──
    {"name": "AI Policy Exchange",     "url": "https://aipolicyexchange.org/feed/"},
    {"name": "Future of Life Inst",    "url": "https://futureoflife.org/feed/"},
]

CORPORATE_KEYWORDS = [
    "layoff","layoffs","laid off","job cuts","firing","redundan","retrench",
    "hiring","recruitment","new jobs","headcount","talent",
    "acquisition","merger","acquires","takeover","deal worth","buys",
    "partnership","joint venture","contract won",
    "earnings","revenue","profit","loss","quarterly","annual results",
    "beats estimates","misses estimates","guidance","forecast",
    "ceo","cfo","cto","coo","resigns","appointed","steps down","fired",
    "bankruptcy","chapter 11","credit rating","downgrade","default",
    "ipo","spac","fundraising","raises","series","valuation",
    "expansion","new market","launches in","opens office",
    "strike","union","workers","employees",
    "fine","lawsuit","penalty","investigation","antitrust",
    "dividend","buyback","shares","stock",
]

AI_KEYWORDS = [
    "gpt","claude","gemini","llama","mistral","grok",
    "llm","large language model","foundation model",
    "artificial intelligence","machine learning","deep learning",
    "ai model","new model","benchmark","surpasses","beats",
    "openai","anthropic","deepmind","meta ai","xai","cohere",
    "funding","raises","billion","million","valuation","ipo",
    "regulation","ban","law","policy","safety","alignment",
    "open source","release","launch","available","update",
    "nvidia","amd","intel","gpu","chip","semiconductor","h100","b200",
    "agent","autonomous","agentic","robotics","humanoid",
    "agi","superintelligence","multimodal","reasoning",
    "copyright","lawsuit","legal","ftc",
    "chatgpt","copilot","gemini","perplexity","cursor",
    "inference","training","fine-tuning","rlhf","rag",
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
X_POST: [punchy viral tweet under 260 chars, no hashtags, make people stop scrolling]
LINKEDIN_POST: [3 sentences sharp insight for executives and investors]"""
    else:
        prompt = f"""Analyze this AI news for a tech and finance audience.
Headline: {headline}
Source: {source}

Reply in EXACTLY this format, nothing else:
MARKET_IMPACT: [2 sentences on which companies are affected]
INDUSTRY_SHIFT: [1 sentence on long term AI industry impact]
HIDDEN_ANGLE: [1 sentence most people miss]
X_POST: [punchy viral tweet under 260 chars, no hashtags, connect to bigger AI race]
LINKEDIN_POST: [3 sentences sharp insight for tech leaders and investors]"""

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
            for entry in feed.entries[:10]:
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
                time.sleep(3)
        except Exception as e:
            print(f"Error {src['name']}: {e}")
    if len(seen) > 10000:
        seen.clear()
    return sent

def main():
    print("=" * 60)
    print("Corp + AI Monitor — MAXIMUM COVERAGE EDITION")
    print(f"Corporate sources: {len(CORPORATE_SOURCES)}")
    print(f"AI sources: {len(AI_SOURCES)}")
    print(f"Powered by: Groq AI (FREE)")
    print(f"Max age: {MAX_AGE_HOURS}h | Interval: {CHECK_INTERVAL//60}min")
    print("=" * 60)

    send_telegram(f"""🚀 *Corp + AI Monitor — MAX COVERAGE ONLINE*
━━━━━━━━━━━━━━━━━━━━
✅ {len(CORPORATE_SOURCES)} Corporate sources worldwide
✅ {len(AI_SOURCES)} AI sources worldwide
✅ Powered by Groq AI — 100% FREE forever
✅ Fresh news only (last 12 hours)
✅ Full analysis on every alert
✅ Ready X post + LinkedIn post

*Coverage:*
🇺🇸 USA — Reuters, WSJ, Bloomberg, CNBC, Forbes
🇬🇧 Europe — FT, Economist, BBC, Guardian
🌏 Asia — Nikkei, SCMP, Straits Times
🇮🇳 India — ET, Moneycontrol, BS, Mint, Inc42
🌍 Middle East — Arabian Business, Gulf News
🌍 Africa — Business Day, African Business
🤖 AI — OpenAI, Anthropic, DeepMind, NVIDIA + 46 more

Scanning every 30 minutes...
⚡ _Your unfair advantage starts now_""")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(CORPORATE_SOURCES)} corporate + {len(AI_SOURCES)} AI sources...")
        c = scan(CORPORATE_SOURCES, CORPORATE_KEYWORDS, "CORPORATE")
        time.sleep(10)
        a = scan(AI_SOURCES, AI_KEYWORDS, "AI")
        print(f"Done. {c+a} alerts. Sleeping {CHECK_INTERVAL//60}min...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
