"""
ingest.py — RSS fetching, article fetching, extraction, summarization, embedding.

Responsible for getting articles into the database. Clustering and AI grouping
logic lives in cluster.py.
"""

import json
import time
import hashlib
import requests
import certifi
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from openai import OpenAI

from config import (
    HEADERS, STRIP_PARAMS, MIN_WORD_COUNT, MAX_FEED_FAILURES,
    OPENAI_API_KEY,
)

_openai = OpenAI(api_key=OPENAI_API_KEY)

_feed_failures: dict[str, int] = {}


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """Strip tracking params and fragment."""
    parsed = urlparse(url)
    qs = {k: v for k, v in parse_qs(parsed.query).items() if k not in STRIP_PARAMS}
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True), fragment=""))


def resolve_google_news_url(url: str) -> str:
    """
    Google News RSS wraps each link in a redirect.
    Use a streaming GET to follow HTTP redirects cheaply (no body download).
    If still on Google after redirects, sniff og:url from a small HTML chunk.
    Returns the resolved URL or the original on failure.
    """
    if "news.google.com" not in url:
        return url
    try:
        with requests.get(url, timeout=(5, 10), headers=HEADERS,
                          allow_redirects=True, stream=True) as resp:
            final = normalize_url(resp.url)
            if "news.google.com" not in final:
                return final
            chunk = next(resp.iter_content(chunk_size=8192), b"")

        soup = BeautifulSoup(chunk, "html.parser")
        for tag in [
            soup.find("meta", property="og:url"),
            soup.find("link", rel="canonical"),
        ]:
            if tag:
                val = tag.get("content") or tag.get("href", "")
                if val and "google.com" not in val:
                    return normalize_url(val)
    except Exception as e:
        print(f"  [gnews-resolve] {url[:80]}: {e}")
    return url


def _strip_publisher_suffix(title: str) -> str:
    """Remove trailing ' - Publisher Name' that news sites append to <title> tags."""
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2 and len(parts[0].strip()) > 10:
        return parts[0].strip()
    return title


def strip_html(html_str: str) -> str:
    """Strip HTML tags from RSS description/summary fields."""
    return BeautifulSoup(html_str, "html.parser").get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_page(url: str, retries=3) -> tuple[str, str]:
    """
    Fetch URL, follow redirects, return (html, canonical_url).
    Raises on permanent failures. Exponential backoff for transient ones.
    """
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                timeout=(5, 25),
                verify=certifi.where(),
                headers=HEADERS,
                allow_redirects=True,
            )
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                raise ValueError(f"Non-HTML content-type: {content_type}")
            resp.raise_for_status()
            return resp.text, normalize_url(resp.url)

        except (requests.exceptions.TooManyRedirects, ValueError):
            raise

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403, 404, 410, 451):
                raise
            print(f"  [http-{e.response.status_code} attempt {attempt + 1}] {url[:80]}")

        except requests.exceptions.Timeout:
            print(f"  [timeout attempt {attempt + 1}] {url[:80]}")

        except Exception as e:
            print(f"  [error attempt {attempt + 1}] {url[:80]}: {e}")

        if attempt < retries - 1:
            time.sleep(2 ** attempt)

    raise Exception(f"Failed after {retries} retries: {url}")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

_CONSENT_PHRASES = [
    "california privacy", "california residents", "ccpa",
    "we value your privacy", "privacy preference", "consent to the use",
    "we use cookies", "cookie policy", "opt-in", "personal data",
    "gdpr", "accept cookies", "manage preferences", "legitimate interest",
]


def is_consent_wall(text: str) -> bool:
    """Return True if extracted text looks like a cookie/privacy consent page."""
    lower = text.lower()
    matches = sum(1 for phrase in _CONSENT_PHRASES if phrase in lower)
    return matches >= 2 and len(text.split()) < 400


def clean_text(html: str) -> str:
    """Extract article body. Strips boilerplate, tries semantic containers first."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside",
                     "noscript", "form", "button", "iframe", "figure"]):
        tag.decompose()

    for selector in [
        "article", "main", '[role="main"]',
        ".article-body", ".article__body", ".story-body",
        ".post-content", ".entry-content",
        "#article-body", "#content",
        ".ArticleBody-articleBody", ".article-content",
    ]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator=" ", strip=True)
            if len(text.split()) > 50:
                return text

    body = soup.find("body")
    return (body or soup).get_text(separator=" ", strip=True)


def extract_article_date(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            for field in ("datePublished", "dateModified", "uploadDate"):
                if field in data:
                    return datetime.fromisoformat(data[field].replace("Z", "+00:00"))
        except Exception:
            pass
    for attr, name in [
        ("property", "article:published_time"),
        ("name", "pubdate"),
        ("name", "date"),
        ("itemprop", "datePublished"),
    ]:
        tag = soup.find("meta", {attr: name})
        if tag and tag.get("content"):
            try:
                return datetime.fromisoformat(tag["content"].replace("Z", "+00:00"))
            except Exception:
                pass
    return None


def extract_title(html: str):
    tag = BeautifulSoup(html, "html.parser").find("title")
    return tag.get_text(strip=True) if tag else None


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# AI — article-level (summarize + embed)
# ---------------------------------------------------------------------------

def summarize(text: str, source_type="news") -> str:
    if source_type == "opinion":
        prompt = (
            "Summarize the following opinion piece in 3-4 sentences, "
            "including the author's main argument. Include any specific numbers, "
            "counts, or statistics mentioned. Respond with only the summary, no preamble:\n\n"
            f"{text[:4000]}"
        )
    else:
        prompt = (
            "Summarize the following article in 3 sentences. Include any specific "
            "numbers, counts, or statistics mentioned. Respond with only the summary, "
            "no preamble:\n\n"
            f"{text[:4000]}"
        )
    resp = _openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


def get_embedding(text: str) -> list:
    resp = _openai.embeddings.create(
        model="text-embedding-3-small",
        input=text[:2000],
    )
    return resp.data[0].embedding


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _upsert_page(url: str, source_domain: str, cur) -> int:
    cur.execute("""
        INSERT INTO pages (url, source_domain)
        VALUES (%s, %s)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
    """, (url, source_domain))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT id FROM pages WHERE url = %s", (url,))
    return cur.fetchone()[0]


def _already_seen(page_id: int, content_hash: str, entry_guid, cur) -> bool:
    cur.execute(
        "SELECT 1 FROM page_versions WHERE page_id = %s AND content_hash = %s",
        (page_id, content_hash),
    )
    if cur.fetchone():
        return True
    if entry_guid:
        cur.execute(
            "SELECT 1 FROM page_versions WHERE page_id = %s AND entry_guid = %s",
            (page_id, entry_guid),
        )
        if cur.fetchone():
            return True
    return False


# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------

def process_url(url: str, cur, conn, title_override=None, date_override=None,
                source_type="news", feed_url=None, entry_guid=None,
                rss_summary: Optional[str] = None,
                rss_source_url: Optional[str] = None) -> str:
    """
    Full ingestion pipeline for one URL.

    Returns: 'duplicate' | 'full' | 'extract_short' | 'fetch_failed'

    RSS metadata is always persisted even when the full pipeline fails.
    """
    resolved = resolve_google_news_url(url)
    canonical_url = normalize_url(resolved)
    source_domain = urlparse(canonical_url).netloc.replace("www.", "")

    # If still on Google (resolution failed), use the RSS <source> URL
    if "google.com" in source_domain and rss_source_url:
        canonical_url = normalize_url(rss_source_url)
        source_domain = urlparse(canonical_url).netloc.replace("www.", "")
        resolved = rss_source_url

    if entry_guid:
        cur.execute("SELECT 1 FROM page_versions WHERE entry_guid = %s", (entry_guid,))
        if cur.fetchone():
            return 'duplicate'

    page_id = _upsert_page(canonical_url, source_domain, cur)

    # ---- Attempt full fetch ----
    html = None
    fetch_error = None
    try:
        html, canonical_url = fetch_page(resolved)
        source_domain = urlparse(canonical_url).netloc.replace("www.", "")
        page_id = _upsert_page(canonical_url, source_domain, cur)
    except Exception as e:
        fetch_error = str(e)

    if html is None:
        rss_text = strip_html(rss_summary) if rss_summary else ""
        content_hash = hash_content(rss_text or canonical_url)

        if _already_seen(page_id, content_hash, entry_guid, cur):
            return 'duplicate'

        embed_text = " ".join(filter(None, [title_override, rss_text]))
        embedding = get_embedding(embed_text) if embed_text.strip() else None

        cur.execute("""
            INSERT INTO page_versions
                (page_id, content_hash, summary, embedding, article_date,
                 feed_url, entry_guid, word_count, ingest_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'fetch_failed')
        """, (page_id, content_hash,
              rss_text[:500] if rss_text else None, embedding,
              date_override, feed_url, entry_guid,
              len(rss_text.split()) if rss_text else 0))

        cur.execute("""
            UPDATE pages
            SET title = COALESCE(title, %s),
                last_fetch_error = %s,
                fetch_fail_count = COALESCE(fetch_fail_count, 0) + 1
            WHERE id = %s
        """, (title_override, fetch_error, page_id))

        conn.commit()
        print(f"  [fetch-failed] {source_domain}: {(title_override or canonical_url)[:70]}")
        return 'fetch_failed'

    # ---- Extraction ----
    text = clean_text(html)
    word_count = len(text.split())
    content_hash = hash_content(text)

    if _already_seen(page_id, content_hash, entry_guid, cur):
        return 'duplicate'

    if is_consent_wall(text):
        print(f"  [consent-wall] {source_domain}: {(title_override or canonical_url)[:70]}")
        conn.rollback()
        return 'fetch_failed'

    if word_count < MIN_WORD_COUNT:
        rss_text = strip_html(rss_summary) if rss_summary else ""
        embed_text = " ".join(filter(None, [title_override or extract_title(html), rss_text]))
        embedding = get_embedding(embed_text) if embed_text.strip() else None

        cur.execute("""
            INSERT INTO page_versions
                (page_id, content_hash, summary, embedding, article_date,
                 feed_url, entry_guid, word_count, ingest_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'extract_short')
        """, (page_id, content_hash,
              (rss_text[:500] if rss_text else None), embedding,
              date_override or extract_article_date(html),
              feed_url, entry_guid, word_count))

        cur.execute("""
            UPDATE pages
            SET title = %s, source_domain = %s,
                fetch_fail_count = 0, last_fetch_error = NULL, updated_at = NOW()
            WHERE id = %s
        """, (title_override or extract_title(html), source_domain, page_id))

        conn.commit()
        print(f"  [short:{word_count}w] {source_domain}: {(title_override or canonical_url)[:70]}")
        return 'extract_short'

    # ---- Full AI pipeline ----
    title = extract_title(html) or title_override
    title = _strip_publisher_suffix(title) if title else title
    article_date = date_override or extract_article_date(html)
    summary = summarize(text, source_type=source_type)
    summary_hash = hash_content(summary)
    embedding = get_embedding(summary)

    cur.execute("""
        INSERT INTO page_versions
            (page_id, content_hash, summary, summary_hash,
             embedding, article_date, feed_url, entry_guid, word_count, ingest_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'full')
    """, (page_id, content_hash, summary, summary_hash,
          embedding, article_date, feed_url, entry_guid, word_count))

    cur.execute("""
        UPDATE pages
        SET title = %s, latest_content_hash = %s, latest_summary_hash = %s,
            source_domain = %s, fetch_fail_count = 0, last_fetch_error = NULL,
            updated_at = NOW()
        WHERE id = %s
    """, (title, content_hash, summary_hash, source_domain, page_id))

    conn.commit()
    print(f"  [full] {source_domain}: {(title or canonical_url)[:70]} ({word_count}w)")
    return 'full'


def process_rss_feed(feed_url: str, cur, conn):
    global _feed_failures

    if _feed_failures.get(feed_url, 0) >= MAX_FEED_FAILURES:
        print(f"\n[quarantine] {feed_url} (failed {MAX_FEED_FAILURES}x this run)")
        return

    print(f"\n[feed] {feed_url}")
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        _feed_failures[feed_url] = _feed_failures.get(feed_url, 0) + 1
        print(f"  [bozo] no entries: {feed.bozo_exception} (failure #{_feed_failures[feed_url]})")
        return

    is_substack = "substack.com" in feed_url
    source_type = "opinion" if is_substack else "news"
    is_google_news = "news.google.com" in feed_url
    counts: dict[str, int] = {}

    print(f"  {len(feed.entries)} entries")
    seen_guids: set[str] = set()

    for entry in feed.entries:
        url = entry.get("link")
        if not url:
            continue

        guid = entry.get("id") or url
        if guid in seen_guids:
            continue
        seen_guids.add(guid)

        title = entry.get("title")
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        date = datetime(*published[:6]) if published else None

        rss_source = entry.get("source", {})
        rss_source_url = rss_source.get("href") or rss_source.get("url")
        rss_source_name = rss_source.get("title", "")

        if is_google_news:
            if title and rss_source_name and title.endswith(f" - {rss_source_name}"):
                title = title[: -len(f" - {rss_source_name}")]
            rss_summary = ""
        else:
            rss_summary = entry.get("summary") or entry.get("description") or ""

        try:
            status = process_url(
                url, cur, conn,
                title_override=title,
                date_override=date,
                source_type=source_type,
                feed_url=feed_url,
                entry_guid=guid,
                rss_summary=rss_summary,
                rss_source_url=rss_source_url,
            )
            counts[status] = counts.get(status, 0) + 1
        except Exception as e:
            print(f"  [skip] {url[:80]}: {e}")
            counts["error"] = counts.get("error", 0) + 1
            conn.rollback()

    summary_parts = [f"{v} {k}" for k, v in sorted(counts.items()) if v]
    print(f"  → {', '.join(summary_parts)}")


def reset_feed_failures():
    global _feed_failures
    _feed_failures = {}


def get_feed_failures() -> dict[str, int]:
    return dict(_feed_failures)
