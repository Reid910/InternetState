"""
Unit tests for api/main.py — no real DB or OpenAI calls.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

# Set dummy env vars before main.py is imported so OpenAI() doesn't raise
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")

from fastapi.testclient import TestClient
import main as api_main


@pytest.fixture
def client():
    api_main._cache.clear()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    with patch("main.get_conn", return_value=mock_conn):
        yield TestClient(api_main.app), mock_cur


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

def test_stats_returns_expected_fields(client):
    test_client, mock_cur = client
    mock_cur.fetchone.return_value = {"total_articles": 1200, "articles_today": 80}
    # Clear cache so we hit the mock

    resp = test_client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_articles" in data
    assert "articles_today" in data

def test_stats_returns_integers(client):
    test_client, mock_cur = client
    mock_cur.fetchone.return_value = {"total_articles": 500, "articles_today": 30}

    resp = test_client.get("/stats")
    data = resp.json()
    assert isinstance(data["total_articles"], int)
    assert isinstance(data["articles_today"], int)


# ---------------------------------------------------------------------------
# /articles
# ---------------------------------------------------------------------------

def test_articles_returns_expected_shape(client):
    test_client, mock_cur = client
    mock_cur.fetchone.side_effect = [
        {"count": 100},
    ]
    mock_cur.fetchall.return_value = [
        {
            "id": 1, "url": "https://example.com/article",
            "title": "Test Article", "source_domain": "example.com",
            "summary": "A summary.", "article_date": None, "fetched_at": None,
        }
    ]

    resp = test_client.get("/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert "articles" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["articles"], list)

def test_articles_pagination_params(client):
    test_client, mock_cur = client
    mock_cur.fetchone.return_value = {"count": 0}
    mock_cur.fetchall.return_value = []

    resp = test_client.get("/articles?page=2&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["limit"] == 10


# ---------------------------------------------------------------------------
# /stories
# ---------------------------------------------------------------------------

def test_stories_returns_expected_shape(client):
    test_client, mock_cur = client
    mock_cur.fetchone.return_value = {"count": 5}
    mock_cur.fetchall.return_value = [
        {
            "id": 1, "headline": "Test Story", "summary": "A summary.",
            "article_count": 3, "updated_at": "2024-06-01T12:00:00",
            "articles": [],
        }
    ]

    resp = test_client.get("/stories")
    assert resp.status_code == 200
    data = resp.json()
    assert "stories" in data
    assert "total" in data
    assert isinstance(data["stories"], list)


# ---------------------------------------------------------------------------
# /stories/{id} — 404 handling
# ---------------------------------------------------------------------------

def test_story_detail_404(client):
    test_client, mock_cur = client
    mock_cur.fetchone.return_value = None

    resp = test_client.get("/stories/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /search — validation
# ---------------------------------------------------------------------------

def test_search_requires_q(client):
    test_client, _ = client
    resp = test_client.get("/search")
    assert resp.status_code == 422  # FastAPI validation error (missing required param)

def test_search_empty_q_returns_400(client):
    test_client, _ = client
    resp = test_client.get("/search?q=")
    assert resp.status_code == 400

def test_search_returns_articles_shape(client):
    test_client, mock_cur = client
    mock_cur.fetchall.return_value = [
        {
            "id": 1, "url": "https://example.com", "title": "Test",
            "source_domain": "example.com", "summary": "Summary.",
            "article_date": None, "fetched_at": None, "score": 0.9,
        }
    ]
    resp = test_client.get("/search?q=test&mode=text&type=articles")
    assert resp.status_code == 200
    data = resp.json()
    assert "articles" in data
    assert data["q"] == "test"

def test_search_returns_stories_shape(client):
    test_client, mock_cur = client
    mock_cur.fetchall.return_value = [
        {
            "id": 1, "headline": "Test Story", "summary": "Summary.",
            "article_count": 2, "updated_at": "2024-06-01", "score": 0.8,
            "articles": [],
        }
    ]
    resp = test_client.get("/search?q=test&mode=text&type=stories")
    assert resp.status_code == 200
    data = resp.json()
    assert "stories" in data
