# Internet State — Plan

## What This Is

An RSS reader that automatically ingests articles from multiple news sources, deduplicates them,
summarizes them with the OpenAI API, groups them into stories, and displays them in a frontend
that shows which media tiers (legacy vs. independent) covered each story and how their framing differs.

Portfolio-ready. Cheap to run. Easy to explain on a resume.

## Current Architecture (Local / Docker)

```text
RSS Feeds
   ↓
Python worker (polls every 15 min)
   ↓  fetches, extracts, deduplicates
OpenAI API (gpt-4o-mini)
   ↓  summarizes + embeds
PostgreSQL + pgvector
   ↓  stores articles, stories, embeddings
FastAPI
   ↓  serves JSON
Next.js frontend
   ↓  displays stories, angles, coverage gaps
```

Everything runs locally via `docker-compose.yml`. The worker, API, Postgres, and frontend
are all separate containers.

## Target Architecture (AWS + Neon)

```text
RSS Feeds
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
AWS S3 + CloudFront              ← static Next.js export, free tier
```

### Why This Stack

- **Lambda + EventBridge** replaces the `while True` polling loop — no always-on server needed.
- **Neon** provides managed pgvector for free. RDS with pgvector costs $20+/month minimum.
- **S3 + CloudFront** hosts the static Next.js build for essentially $0.
- AWS services on resume: Lambda, EventBridge Scheduler, API Gateway, S3, CloudFront.

### Estimated Monthly Cost

| Item | Cost |
|---|---|
| AWS Lambda, EventBridge, API Gateway, S3, CloudFront | ~$0 (free tier) |
| Neon PostgreSQL | $0 (free tier) |
| OpenAI API (gpt-4o-mini summaries + embeddings) | ~$0.10–0.25 |
| **Total** | **~$0.25/month** |

## Database Schema

Managed by sequential SQL migrations in `postgres/init/`.

### Core Tables

**`pages`** — one row per unique article URL.

```text
id, url, title, source_domain, media_tier,
latest_content_hash, latest_summary_hash,
fetch_fail_count, last_fetch_error,
created_at, updated_at
```

**`page_versions`** — one row per fetch of a page. Stores extracted text, summary, and embedding.

```text
id, page_id, content_hash, clean_text,
summary, summary_hash, embedding (vector 1536),
article_date, feed_url, entry_guid, word_count,
ingest_status ('full' | 'extract_short' | 'fetch_failed'),
fetched_at
```

**`stories`** — AI-grouped clusters of articles covering the same event.

```text
id, headline, summary, coverage_tiers, media_comparison,
last_seen, created_at
```

**`story_articles`** — links articles to stories, optionally to an angle within that story.

```text
story_id, page_id, angle_id
```

**`story_angles`** — named sub-facets within a story (e.g. "Economic impact", "Political reaction").

```text
id, story_id, title, summary, last_seen, created_at
```

**`coverage_reports`** — one row per clustering run, summarizing media tier gaps.

```text
id, created_at, legacy_only_count, independent_only_count,
both_count, gap_analysis
```

### Embedding Dimensions

Using OpenAI `text-embedding-3-small` → `vector(1536)`.
Schema uses `vector(1536)` in `page_versions.embedding`.

## AI Usage

### Summarization

Model: `gpt-4o-mini`

Called once per new article after deduplication check. Input is up to 4000 chars of extracted
article text. Returns a 3-sentence plain English summary.

Opinion/Substack articles get a slightly different prompt that captures the author's main argument.

### Embeddings

Model: `text-embedding-3-small`

Called once per new article on the summary text (or RSS metadata if fetch failed).
Stored as `vector(1536)` in `page_versions.embedding`.
Used for semantic similarity when clustering articles into stories.

### Story Clustering (cluster.py — currently commented out)

Groups articles into stories using embedding cosine similarity.
Generates story headline, summary, and per-angle breakdowns via GPT.
Generates a coverage gap analysis comparing legacy vs. independent framing.

## Source Classification

Sources are classified as `legacy`, `independent`, or `aggregator` in `config.py`.
The `media_tier` column on `pages` is set at ingest time based on the source domain.

Stories track which tiers covered them (`coverage_tiers`) and AI-generated framing
differences (`media_comparison`) when both tiers are present.

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

## Deployment Tasks

### 1. Switch Ollama → OpenAI

In `worker/ingest.py`:
- Replace `summarize()` — swap Ollama `/api/generate` call for OpenAI Chat Completions.
- Replace `get_embedding()` — swap Ollama `/api/embed` for OpenAI `text-embedding-3-small`.

In `postgres/init/001_schema.sql`:
- Update `embedding vector(384)` → `vector(1536)`.

Add `OPENAI_API_KEY` to worker environment.

### 2. Convert Worker to Lambda

- Extract the per-run logic from `main.py` into a Lambda handler function.
- Package dependencies with the function (or use a Lambda layer).
- Set `DATABASE_URL` and `OPENAI_API_KEY` as Lambda environment variables (via AWS Secrets Manager
  or SSM Parameter Store).

### 3. Set Up EventBridge Scheduler

- Create a schedule that triggers the worker Lambda every 15 minutes.

### 4. Convert API to Lambda + API Gateway

- Add `mangum` to `api/requirements.txt`.
- Wrap the FastAPI `app` with `Mangum(app)` and export as Lambda handler.
- Deploy behind API Gateway (HTTP API).

### 5. Static Export Next.js → S3 + CloudFront

- Add `output: 'export'` to `frontend/next.config.js`.
- Note: the frontend uses server-side `fetch` in `page.tsx` — this needs to move to client-side
  fetching from `NEXT_PUBLIC_API_URL` for a static export to work.
- Deploy the `out/` folder to S3, serve via CloudFront.

### 6. Neon Database

- Create a Neon project, copy the connection string.
- Run all migrations in `postgres/init/` against the Neon DB.
- Point `DATABASE_URL` in both Lambda functions at Neon.

## RSS Sources

Configured in `worker/config.py` under `RSS_SOURCES`.

Current sources:

- Google News (aggregator)
- Reuters
- The Guardian
- NPR
- BBC World
- Politico
- Al Jazeera
- The Intercept
- ProPublica

## Frontend

Next.js app in `frontend/`. Currently server-rendered with `force-dynamic`.

Pages:
- `/` — stats header, coverage gap report, stories browser

API calls hit FastAPI at `API_URL` (server-side) or `NEXT_PUBLIC_API_URL` (client-side).

For static export deployment, all fetching must move to client-side.

## Project Structure

```text
internet-state/
  plan.md
  docker-compose.yml
  api/
    Dockerfile
    main.py              ← FastAPI app
    requirements.txt
  worker/
    Dockerfile
    main.py              ← entry point, run loop
    ingest.py            ← RSS fetch + AI pipeline
    cluster.py           ← story clustering (commented out)
    config.py            ← sources, constants, env vars
    worker.py            ← SQS polling mode (alternative to sleep loop)
    requirements.txt
  frontend/
    app/
      page.tsx           ← home page
      StoriesBrowser.tsx ← story list component
    next.config.js
  postgres/
    init/
      001_schema.sql     ← pages, page_versions, vector extension
      002_topics.sql     ← stories, story_articles
      003_improvements.sql ← source_domain, ingest_status, story_angles
      004_angles.sql     ← story_angles table + angle_id on story_articles
      005_media_tiers.sql ← media_tier, coverage_tiers, coverage_reports
```

## Resume Bullet

```text
Built a serverless news intelligence platform on AWS (Lambda, EventBridge, API Gateway,
S3, CloudFront) that ingests RSS feeds from 9 sources, deduplicates and summarizes
articles with the OpenAI API, clusters them into stories using pgvector semantic
similarity, and flags coverage gaps between legacy and independent media.
```
