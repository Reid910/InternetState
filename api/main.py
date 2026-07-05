import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

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


handler = Mangum(app)
