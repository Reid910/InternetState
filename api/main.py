import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://internet-state-roan.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@app.get("/stats")
def stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM pages) AS total_articles,
            (SELECT COUNT(*) FROM page_versions
             WHERE fetched_at >= NOW() - INTERVAL '24 hours') AS articles_today
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


@app.get("/articles")
def list_articles(page: int = 1, limit: int = 30, source: str = None):
    offset = (page - 1) * limit
    conn = get_conn()
    cur = conn.cursor()

    source_filter = "AND p.source_domain = %s" if source else ""
    count_params = ([source] if source else [])
    query_params = ([source] if source else []) + [limit, offset]

    cur.execute(f"""
        SELECT COUNT(DISTINCT p.id)
        FROM page_versions pv
        JOIN pages p ON p.id = pv.page_id
        WHERE pv.ingest_status = 'full' {source_filter}
    """, count_params)
    total = cur.fetchone()["count"]

    cur.execute(f"""
        SELECT p.id, p.url, p.title, p.source_domain,
               pv.summary, pv.article_date, pv.fetched_at
        FROM (
            SELECT DISTINCT ON (page_id) *
            FROM page_versions
            WHERE ingest_status = 'full'
            ORDER BY page_id, COALESCE(article_date, fetched_at) DESC
        ) pv
        JOIN pages p ON p.id = pv.page_id
        WHERE true {source_filter}
        ORDER BY COALESCE(pv.article_date, pv.fetched_at) DESC
        LIMIT %s OFFSET %s
    """, query_params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"total": total, "page": page, "limit": limit, "articles": rows}


@app.get("/sources")
def list_sources():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.source_domain, COUNT(*) AS article_count
        FROM page_versions pv
        JOIN pages p ON p.id = pv.page_id
        WHERE p.source_domain IS NOT NULL AND pv.ingest_status = 'full'
        GROUP BY p.source_domain
        ORDER BY article_count DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.get("/stories")
def list_stories(page: int = 1, limit: int = 20):
    offset = (page - 1) * limit
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM stories")
    total = cur.fetchone()["count"]

    cur.execute("""
        SELECT s.id, s.headline, s.summary, s.article_count, s.updated_at,
               json_agg(json_build_object(
                   'id', p.id, 'url', p.url, 'title', p.title,
                   'source_domain', p.source_domain
               ) ORDER BY p.id) AS articles
        FROM stories s
        JOIN story_articles sa ON sa.story_id = s.id
        JOIN pages p ON p.id = sa.page_id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"total": total, "page": page, "limit": limit, "stories": rows}


handler = Mangum(app)
