import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DATABASE_URL", "postgresql://appuser:apppassword@postgres:5432/summarizer")


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@app.get("/stats")
def stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM pages) AS total_articles,
            (SELECT COUNT(*) FROM stories) AS total_stories,
            (SELECT COUNT(*) FROM stories WHERE created_at >= NOW() - INTERVAL '24 hours') AS stories_today
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


@app.get("/articles")
def list_articles(page: int = 1, limit: int = 20):
    offset = (page - 1) * limit
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.url, p.title, p.source_domain,
               pv.summary, pv.article_date, pv.fetched_at, pv.ingest_status
        FROM page_versions pv
        JOIN pages p ON p.id = pv.page_id
        ORDER BY pv.article_date DESC NULLS LAST, pv.fetched_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.get("/coverage-report")
def latest_coverage_report():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_at, legacy_only_count, independent_only_count,
               both_count, gap_analysis
        FROM coverage_reports
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


@app.get("/stories")
def list_stories(page: int = 1, limit: int = 50):
    offset = (page - 1) * limit
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT s.id)
        FROM stories s
        JOIN story_articles sa ON sa.story_id = s.id
    """)
    total = cur.fetchone()["count"]
    cur.execute("""
        SELECT s.id, s.headline, s.summary, s.coverage_tiers, s.media_comparison,
               MAX(COALESCE(pv.article_date, pv.fetched_at)) AS last_seen,
               s.created_at,
               COUNT(sa.page_id) AS article_count
        FROM stories s
        JOIN story_articles sa ON sa.story_id = s.id
        JOIN page_versions pv ON pv.page_id = sa.page_id
        GROUP BY s.id
        ORDER BY MAX(COALESCE(pv.article_date, pv.fetched_at)) DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"total": total, "page": page, "limit": limit, "stories": rows}


@app.get("/stories/{story_id}/angles")
def story_angles(story_id: int):
    """
    Returns angles (named facets) within a story, each with their articles nested.
    A final entry with id=null contains articles not assigned to any angle.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, summary
        FROM story_angles
        WHERE story_id = %s
        ORDER BY created_at ASC
    """, (story_id,))
    angles = cur.fetchall()

    result = []
    for angle in angles:
        cur.execute("""
            SELECT p.id, p.url, p.title, p.source_domain,
                   pv.summary, pv.article_date, pv.ingest_status
            FROM story_articles sa
            JOIN pages p ON p.id = sa.page_id
            JOIN page_versions pv ON pv.page_id = p.id
            WHERE sa.story_id = %s AND sa.angle_id = %s
            ORDER BY pv.article_date DESC NULLS LAST
        """, (story_id, angle["id"]))
        result.append({
            "id": angle["id"],
            "title": angle["title"],
            "summary": angle["summary"],
            "articles": cur.fetchall(),
        })

    # Articles not assigned to any angle
    cur.execute("""
        SELECT p.id, p.url, p.title, p.source_domain,
               pv.summary, pv.article_date, pv.ingest_status
        FROM story_articles sa
        JOIN pages p ON p.id = sa.page_id
        JOIN page_versions pv ON pv.page_id = p.id
        WHERE sa.story_id = %s AND sa.angle_id IS NULL
        ORDER BY pv.article_date DESC NULLS LAST
    """, (story_id,))
    unassigned = cur.fetchall()
    if unassigned:
        result.append({"id": None, "title": None, "summary": None, "articles": unassigned})

    cur.close()
    conn.close()
    return result


@app.get("/stories/{story_id}/articles")
def story_articles(story_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.url, p.title, p.source_domain,
               pv.summary, pv.article_date, pv.ingest_status,
               sa.angle_id
        FROM story_articles sa
        JOIN pages p ON p.id = sa.page_id
        JOIN page_versions pv ON pv.page_id = p.id
        WHERE sa.story_id = %s
        ORDER BY pv.article_date DESC NULLS LAST
    """, (story_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
