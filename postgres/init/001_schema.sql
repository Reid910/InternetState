CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS pages (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    latest_content_hash TEXT,
    latest_summary_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS page_versions (
    id SERIAL PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    fetched_at TIMESTAMP DEFAULT NOW(),
    content_hash TEXT NOT NULL,
    clean_text TEXT NOT NULL,
    summary TEXT,
    summary_hash TEXT,
    status_code INTEGER,
    etag TEXT,
    last_modified TEXT,
    embedding vector(384),
    article_date TIMESTAMP
);
