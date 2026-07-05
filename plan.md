# Internet State — Plan

## What This Is

A serverless news intelligence platform that automatically ingests articles from RSS feeds,
summarizes them with the OpenAI API, and displays them in a live-updating web feed.
Future goal: group articles into story clusters using semantic similarity.

## Architecture

```text
RSS Feeds (9 sources)
   ↓
AWS EventBridge Scheduler        ← triggers every 15 min, free tier
   ↓
AWS Lambda (worker)              ← ingest + summarize, free tier
   ↓
OpenAI API (gpt-4o-mini)        ← ~$0.10–0.25/month
   ↓
Neon PostgreSQL + pgvector       ← free tier, lives outside AWS
   ↓
AWS Lambda + API Gateway         ← FastAPI via Mangum, free tier
   ↓
Vercel (Next.js)                 ← frontend, free tier
```

### Estimated Monthly Cost

| Item | Cost |
|---|---|
| AWS Lambda, EventBridge, API Gateway, ECR | ~$0 (free tier) |
| Neon PostgreSQL | $0 (free tier) |
| OpenAI API (gpt-4o-mini summaries + embeddings) | ~$0.25 |
| Vercel | $0 (free tier) |
| **Total** | **~$0.25/month** |

## Database Schema

### Core Tables

**`pages`** — one row per unique article URL.

```text
id, url, title, source_domain,
latest_content_hash, latest_summary_hash,
fetch_fail_count, last_fetch_error,
created_at, updated_at
```

**`page_versions`** — one row per fetch. Stores extracted text, summary, and embedding.

```text
id, page_id, content_hash, clean_text,
summary, summary_hash, embedding (vector 1536),
article_date, feed_url, entry_guid, word_count,
ingest_status ('full' | 'extract_short' | 'fetch_failed'),
fetched_at
```

**`stories`** — AI-grouped clusters of articles covering the same event.

```text
id, headline, summary, last_seen, created_at
```

**`story_articles`** — links articles to stories.

```text
story_id, page_id, angle_id
```

**`story_angles`** — named sub-facets within a story (e.g. "Economic impact", "Political reaction").

```text
id, story_id, title, summary, last_seen, created_at
```

### Embedding Dimensions

Using OpenAI `text-embedding-3-small` → `vector(1536)`.

## AI Usage

### Summarization

Model: `gpt-4o-mini`

Called once per new article after deduplication check. Input is up to 4000 chars of extracted
article text. Returns a 3-sentence plain English summary.

### Embeddings

Model: `text-embedding-3-small`

Called once per new article on the summary text (or RSS metadata if fetch failed).
Stored as `vector(1536)` in `page_versions.embedding`.
Used for semantic similarity when clustering articles into stories.

## Worker Pipeline (ingest.py)

For each RSS entry:

1. Resolve Google News redirect URLs.
2. Normalize and deduplicate by URL + entry GUID.
3. Fetch full article HTML (with retries, backoff).
4. Extract clean article text (targets semantic HTML containers).
5. Detect and skip cookie/consent walls.
6. If word count is too short, store RSS metadata only.
7. Summarize with OpenAI.
8. Embed summary with OpenAI.
9. Save to Postgres.

Safety limits:
- `MAX_FEED_FAILURES = 3` — quarantines a feed after repeated failures in one run.
- `MIN_WORD_COUNT = 120` — skips AI for articles that extracted too little text.

## RSS Sources

Configured in `worker/config.py` under `RSS_SOURCES`.

- Google News (aggregator)
- AP News
- The Guardian
- NPR
- BBC World
- Politico
- Al Jazeera
- The Intercept
- ProPublica

## Frontend

Next.js app deployed on Vercel at [internet-state-roan.vercel.app](https://internet-state-roan.vercel.app).

- `/` — article feed, source filter dropdown, path-based pagination
- `/2`, `/3`, ... — paginated article pages (30 per page)

## Project Structure

```text
internet-state/
  plan.md
  docker-compose.yml
  api/
    Dockerfile.lambda
    main.py              ← FastAPI app + Mangum handler
    requirements.txt
  worker/
    Dockerfile.lambda
    main.py              ← entry point / run loop
    lambda_handler.py    ← Lambda entry point
    ingest.py            ← RSS fetch + AI pipeline
    config.py            ← sources, constants, env vars
    requirements.txt
  frontend/
    app/
      page.tsx           ← home page
      [page]/page.tsx    ← dynamic pagination route
      ArticleFeed.tsx    ← article list component
    next.config.ts
  postgres/
    init/
      001_schema.sql     ← pages, page_versions, vector extension
      002_topics.sql     ← stories, story_articles
      003_improvements.sql
      004_angles.sql
      005_media_tiers.sql
```

## Roadmap

- **Story clustering** — group articles about the same event using embedding cosine similarity
- **Multi-source comparison** — show how different outlets covered the same story
- **Search** — full-text and semantic search across the article archive
- **Summary styles** — bullet points, ELI5, detailed breakdown
