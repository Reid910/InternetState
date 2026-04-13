import os

RSS_SOURCES = [
    # Legacy / wire
    "https://news.google.com/rss",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.theguardian.com/world/rss",
    "https://feeds.npr.org/1001/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.politico.com/rss/politicopicks.xml",
    # Independent / investigative
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
MIN_ARTICLES_FOR_ANGLES = 3
ANGLE_DISTANCE_THRESHOLD = 0.15
COVERAGE_GAP_THRESHOLD = 0.40

DB_URL = os.getenv("DATABASE_URL", "postgresql://appuser:apppassword@postgres:5432/summarizer")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_URL = os.getenv("SQS_URL", "")

# Curated tier classification. Domains not listed are 'unknown'.
# Edit this dict as you add/remove sources.
MEDIA_TIERS: dict[str, str] = {
    # Legacy / mainstream / wire
    "reuters.com":        "legacy",
    "apnews.com":         "legacy",
    "bbc.com":            "legacy",
    "bbc.co.uk":          "legacy",
    "theguardian.com":    "legacy",
    "npr.org":            "legacy",
    "nytimes.com":        "legacy",
    "washingtonpost.com": "legacy",
    "wsj.com":            "legacy",
    "politico.com":       "legacy",
    "cnn.com":            "legacy",
    "nbcnews.com":        "legacy",
    "abcnews.go.com":     "legacy",
    "cbsnews.com":        "legacy",
    "foxnews.com":        "legacy",
    "bloomberg.com":      "legacy",
    "ft.com":             "legacy",
    "time.com":           "legacy",
    "newsweek.com":       "legacy",
    "usatoday.com":       "legacy",
    "latimes.com":        "legacy",
    "thehill.com":        "legacy",
    "axios.com":          "legacy",
    # Independent / investigative / alternative
    "aljazeera.com":      "independent",
    "theintercept.com":   "independent",
    "propublica.org":     "independent",
    "democracynow.org":   "independent",
    "motherjones.com":    "independent",
    "thenation.com":      "independent",
    "jacobin.com":        "independent",
    "commondreams.org":   "independent",
    "truthout.org":       "independent",
    "mintpressnews.com":  "independent",
    "consortiumnews.com": "independent",
    "scheerpost.com":     "independent",
    "stevenschmidt.substack.com": "independent",
    "racket.news":        "independent",
    "substack.com":       "independent",
    # Aggregators — excluded from tier comparison
    "news.google.com":    "aggregator",
    "reddit.com":         "aggregator",
    "flipboard.com":      "aggregator",
}
