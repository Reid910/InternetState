ALTER TABLE pages ADD COLUMN IF NOT EXISTS source_domain TEXT;
ALTER TABLE pages ADD COLUMN IF NOT EXISTS fetch_fail_count INTEGER DEFAULT 0;
ALTER TABLE pages ADD COLUMN IF NOT EXISTS last_fetch_error TEXT;

ALTER TABLE page_versions ADD COLUMN IF NOT EXISTS feed_url TEXT;
ALTER TABLE page_versions ADD COLUMN IF NOT EXISTS entry_guid TEXT;
ALTER TABLE page_versions ADD COLUMN IF NOT EXISTS word_count INTEGER;

CREATE INDEX IF NOT EXISTS idx_page_versions_entry_guid ON page_versions (entry_guid);
CREATE INDEX IF NOT EXISTS idx_pages_source_domain ON pages (source_domain);
