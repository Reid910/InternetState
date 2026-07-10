import os

RSS_SOURCES = [
    "https://news.google.com/rss",
    "https://apnews.com/rss",
    "https://www.theguardian.com/world/rss",
    "https://feeds.npr.org/1001/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.politico.com/politics-news.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://theintercept.com/feed/?rss",
    "https://www.propublica.org/feeds/propublica/main",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "fbclid", "gclid", "_ga", "mc_cid", "mc_eid", "ref", "source", "via",
}

MIN_WORD_COUNT = 120
MAX_FEED_FAILURES = 3

DB_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
