DROP TABLE IF EXISTS topic_articles;
DROP TABLE IF EXISTS topics;

CREATE TABLE IF NOT EXISTS stories (
    id SERIAL PRIMARY KEY,
    headline TEXT NOT NULL,
    summary TEXT,
    last_seen TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS story_articles (
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    page_id  INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    PRIMARY KEY (story_id, page_id)
);
