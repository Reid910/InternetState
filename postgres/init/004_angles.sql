-- Allow clean_text to be NULL for RSS-only / fetch-failed entries
ALTER TABLE page_versions ALTER COLUMN clean_text DROP NOT NULL;

-- Track how far ingestion got for each page version
-- 'full'         : fetch + extract + summarize + embed all succeeded
-- 'extract_short': fetched but too few words, no AI summary or embedding
-- 'fetch_failed' : could not fetch, stored from RSS metadata only
ALTER TABLE page_versions ADD COLUMN IF NOT EXISTS ingest_status TEXT DEFAULT 'full';

-- Sub-topics within a story — a narrower, named facet
CREATE TABLE IF NOT EXISTS story_angles (
    id          SERIAL PRIMARY KEY,
    story_id    INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    summary     TEXT,
    last_seen   TIMESTAMP DEFAULT NOW(),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_story_angles_story_id ON story_angles(story_id);

-- Link each story<>article row to an optional angle within that story
ALTER TABLE story_articles ADD COLUMN IF NOT EXISTS angle_id INTEGER REFERENCES story_angles(id) ON DELETE SET NULL;
