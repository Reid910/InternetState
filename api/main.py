import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://internet-state-roan.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DATABASE_URL")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@app.get("/stats")
def stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM page_versions WHERE ingest_status = 'full') AS total_articles,
            (SELECT COUNT(*) FROM page_versions
             WHERE ingest_status = 'full' AND fetched_at >= NOW() - INTERVAL '24 hours') AS articles_today
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


@app.get("/search")
def search(q: str, mode: str = "text", type: str = "articles", limit: int = 20):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="q is required")

    conn = get_conn()
    cur = conn.cursor()

    vec_str = None
    if mode == "semantic":
        resp = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=q.strip(),
        )
        vec = resp.data[0].embedding
        vec_str = "[" + ",".join(str(x) for x in vec) + "]"

    if type == "stories":
        if mode == "semantic":
            cur.execute("""
                SELECT s.id, s.headline, s.summary, s.article_count, s.updated_at,
                       1 - (s.embedding <=> %s::vector) AS score,
                       json_agg(json_build_object(
                           'id', p.id, 'url', p.url, 'title', p.title,
                           'source_domain', p.source_domain
                       ) ORDER BY p.id) AS articles
                FROM stories s
                JOIN story_articles sa ON sa.story_id = s.id
                JOIN pages p ON p.id = sa.page_id
                WHERE s.embedding IS NOT NULL
                GROUP BY s.id
                ORDER BY s.embedding <=> %s::vector
                LIMIT %s
            """, (vec_str, vec_str, limit))
        else:
            cur.execute("""
                SELECT s.id, s.headline, s.summary, s.article_count, s.updated_at,
                       ts_rank(
                           to_tsvector('english', coalesce(s.headline,'') || ' ' || coalesce(s.summary,'')),
                           websearch_to_tsquery('english', %s)
                       ) AS score,
                       json_agg(json_build_object(
                           'id', p.id, 'url', p.url, 'title', p.title,
                           'source_domain', p.source_domain
                       ) ORDER BY p.id) AS articles
                FROM stories s
                JOIN story_articles sa ON sa.story_id = s.id
                JOIN pages p ON p.id = sa.page_id
                WHERE to_tsvector('english', coalesce(s.headline,'') || ' ' || coalesce(s.summary,''))
                      @@ websearch_to_tsquery('english', %s)
                GROUP BY s.id
                ORDER BY score DESC
                LIMIT %s
            """, (q, q, limit))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"total": len(rows), "mode": mode, "type": "stories", "q": q, "stories": rows}

    # articles
    if mode == "semantic":
        cur.execute("""
            SELECT p.id, p.url, p.title, p.source_domain,
                   pv.summary, pv.article_date, pv.fetched_at,
                   1 - (pv.embedding <=> %s::vector) AS score
            FROM (
                SELECT DISTINCT ON (page_id) *
                FROM page_versions
                WHERE ingest_status = 'full' AND embedding IS NOT NULL
                ORDER BY page_id, COALESCE(article_date, fetched_at) DESC
            ) pv
            JOIN pages p ON p.id = pv.page_id
            ORDER BY pv.embedding <=> %s::vector
            LIMIT %s
        """, (vec_str, vec_str, limit))
    else:
        cur.execute("""
            SELECT p.id, p.url, p.title, p.source_domain,
                   pv.summary, pv.article_date, pv.fetched_at,
                   ts_rank(
                       to_tsvector('english', coalesce(p.title,'') || ' ' || coalesce(pv.summary,'')),
                       websearch_to_tsquery('english', %s)
                   ) AS score
            FROM (
                SELECT DISTINCT ON (page_id) *
                FROM page_versions
                WHERE ingest_status = 'full'
                ORDER BY page_id, COALESCE(article_date, fetched_at) DESC
            ) pv
            JOIN pages p ON p.id = pv.page_id
            WHERE to_tsvector('english', coalesce(p.title,'') || ' ' || coalesce(pv.summary,''))
                  @@ websearch_to_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
        """, (q, q, limit))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"total": len(rows), "mode": mode, "type": "articles", "q": q, "articles": rows}


handler = Mangum(app)
