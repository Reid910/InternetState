-- Media tier classification per source domain
ALTER TABLE pages ADD COLUMN IF NOT EXISTS media_tier TEXT;  -- 'legacy', 'independent', 'aggregator'

-- Per-story: which tiers covered it, AI-generated comparisons
ALTER TABLE stories ADD COLUMN IF NOT EXISTS coverage_tiers TEXT;       -- 'legacy_only', 'independent_only', 'both'
ALTER TABLE stories ADD COLUMN IF NOT EXISTS media_comparison TEXT;     -- framing diff when both tiers present

-- Per-run coverage gap report
CREATE TABLE IF NOT EXISTS coverage_reports (
    id          SERIAL PRIMARY KEY,
    created_at  TIMESTAMP DEFAULT NOW(),
    legacy_only_count    INTEGER,
    independent_only_count INTEGER,
    both_count           INTEGER,
    gap_analysis         TEXT        -- AI narrative about what each tier covered/ignored
);

CREATE INDEX IF NOT EXISTS idx_pages_media_tier ON pages(media_tier);
CREATE INDEX IF NOT EXISTS idx_stories_coverage_tiers ON stories(coverage_tiers);
