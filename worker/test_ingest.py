"""
Unit tests for ingest.py — no network, no DB, no OpenAI calls.
"""
import pytest
from unittest.mock import MagicMock, patch
from ingest import (
    normalize_url,
    _strip_publisher_suffix,
    is_consent_wall,
    clean_text,
    hash_content,
    _already_seen,
    _as_utc,
    extract_article_date,
)
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------

def test_normalize_url_strips_utm():
    url = "https://example.com/article?utm_source=twitter&utm_medium=social"
    assert "utm_source" not in normalize_url(url)
    assert "utm_medium" not in normalize_url(url)

def test_normalize_url_strips_fragment():
    url = "https://example.com/article#section-2"
    assert "#" not in normalize_url(url)

def test_normalize_url_keeps_real_params():
    url = "https://example.com/article?id=123"
    assert "id=123" in normalize_url(url)

def test_normalize_url_passthrough():
    url = "https://example.com/article"
    assert normalize_url(url) == url


# ---------------------------------------------------------------------------
# _strip_publisher_suffix
# ---------------------------------------------------------------------------

def test_strip_publisher_suffix_removes_suffix():
    title = "Breaking: Something Happened - The Guardian"
    assert _strip_publisher_suffix(title) == "Breaking: Something Happened"

def test_strip_publisher_suffix_keeps_short_result():
    # If the part before the dash is too short, keep the original
    title = "AI - NPR"
    assert _strip_publisher_suffix(title) == "AI - NPR"

def test_strip_publisher_suffix_no_dash():
    title = "Just a headline with no publisher"
    assert _strip_publisher_suffix(title) == title


# ---------------------------------------------------------------------------
# is_consent_wall
# ---------------------------------------------------------------------------

def test_is_consent_wall_detects_gdpr_page():
    text = (
        "We use cookies to improve your experience. "
        "This site uses GDPR compliant cookie policy. "
        "Please accept cookies to continue. " * 10
    )
    assert is_consent_wall(text) is True

def test_is_consent_wall_passes_real_article():
    text = (
        "The president signed a new bill into law today. "
        "The legislation affects millions of Americans. "
        "Lawmakers debated for weeks before reaching agreement. "
    ) * 50  # long enough to not be flagged
    assert is_consent_wall(text) is False

def test_is_consent_wall_requires_multiple_phrases():
    # Only one consent phrase — should not trigger
    text = "We use cookies. " + "Real article content. " * 50
    assert is_consent_wall(text) is False


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

def test_clean_text_strips_script_tags():
    html = "<html><body><script>alert('x')</script><article>Real content here</article></body></html>"
    result = clean_text(html)
    assert "alert" not in result
    assert "Real content here" in result

def test_clean_text_prefers_article_tag():
    html = """
    <html><body>
      <nav>Navigation stuff</nav>
      <article>This is the article body with enough words to pass the threshold and be selected as the main content.</article>
      <footer>Footer stuff</footer>
    </body></html>
    """
    result = clean_text(html)
    assert "article body" in result
    assert "Navigation stuff" not in result
    assert "Footer stuff" not in result

def test_clean_text_falls_back_to_body():
    html = "<html><body><p>Just some text with no semantic containers.</p></body></html>"
    result = clean_text(html)
    assert "Just some text" in result


# ---------------------------------------------------------------------------
# hash_content
# ---------------------------------------------------------------------------

def test_hash_content_deterministic():
    assert hash_content("hello") == hash_content("hello")

def test_hash_content_different_inputs():
    assert hash_content("hello") != hash_content("world")

def test_hash_content_returns_string():
    assert isinstance(hash_content("test"), str)


# ---------------------------------------------------------------------------
# _as_utc
# ---------------------------------------------------------------------------

def test_as_utc_naive_datetime_gets_utc():
    dt = datetime(2024, 1, 15, 12, 0, 0)
    result = _as_utc(dt)
    assert result.tzinfo == timezone.utc

def test_as_utc_aware_datetime_converts():
    from datetime import timedelta
    tz = timezone(timedelta(hours=5))
    dt = datetime(2024, 1, 15, 17, 0, 0, tzinfo=tz)
    result = _as_utc(dt)
    assert result.tzinfo == timezone.utc
    assert result.hour == 12  # 17:00+05:00 = 12:00 UTC


# ---------------------------------------------------------------------------
# _already_seen
# ---------------------------------------------------------------------------

def test_already_seen_by_content_hash():
    cur = MagicMock()
    cur.fetchone.return_value = (1,)
    assert _already_seen(42, "abc123", None, cur) is True

def test_already_seen_by_guid():
    cur = MagicMock()
    # First call (content hash): no match. Second call (guid): match.
    cur.fetchone.side_effect = [None, (1,)]
    assert _already_seen(42, "abc123", "some-guid", cur) is True

def test_not_already_seen():
    cur = MagicMock()
    cur.fetchone.return_value = None
    assert _already_seen(42, "abc123", "some-guid", cur) is False


# ---------------------------------------------------------------------------
# extract_article_date
# ---------------------------------------------------------------------------

def test_extract_article_date_from_ld_json():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "NewsArticle", "datePublished": "2024-06-15T10:30:00Z"}
    </script>
    </head><body></body></html>
    """
    result = extract_article_date(html)
    assert result is not None
    assert result.year == 2024
    assert result.month == 6
    assert result.day == 15
    assert result.tzinfo == timezone.utc

def test_extract_article_date_from_meta_tag():
    html = """
    <html><head>
    <meta property="article:published_time" content="2024-03-20T08:00:00+00:00" />
    </head><body></body></html>
    """
    result = extract_article_date(html)
    assert result is not None
    assert result.year == 2024
    assert result.month == 3

def test_extract_article_date_returns_none_when_missing():
    html = "<html><head></head><body>No date here</body></html>"
    assert extract_article_date(html) is None
