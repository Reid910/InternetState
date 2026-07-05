# Internet State

A serverless news intelligence platform that automatically ingests articles from RSS feeds, summarizes them with AI, and displays them in a live-updating web feed.

**Live site:** internet-state-roan.vercel.app

---

## What It Does

- Fetches articles from 9 RSS news sources every 15 minutes
- Extracts full article text, deduplicates by URL and GUID
- Summarizes each new article using the OpenAI API
- Generates vector embeddings for semantic similarity (groundwork for story clustering)
- Serves articles through a REST API with source filtering and pagination
- Displays a live article feed at a public URL

---

## Architecture

```
RSS Feeds (9 sources)
   ↓
AWS EventBridge Scheduler  — fires every 15 minutes
   ↓
AWS Lambda (worker)        — fetches, extracts, deduplicates, summarizes
   ↓
OpenAI API                 — gpt-4o-mini (summaries) + text-embedding-3-small (vectors)
   ↓
Neon PostgreSQL + pgvector — stores articles, summaries, and embeddings
   ↓
AWS Lambda + API Gateway   — FastAPI REST API
   ↓
Vercel (Next.js)           — public frontend
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Ingest worker | Python, feedparser, BeautifulSoup |
| AI summarization | OpenAI gpt-4o-mini |
| Vector embeddings | OpenAI text-embedding-3-small (1536-dim) |
| Database | PostgreSQL + pgvector (Neon) |
| REST API | Python, FastAPI, Mangum |

### AWS Services
| Service | Role |
|---|---|
| **Lambda** | Runs the ingest worker and API |
| **EventBridge Scheduler** | Triggers the worker on a cron schedule (every 15 min) |
| **API Gateway** | HTTP endpoint in front of the FastAPI Lambda |
| **ECR** | Stores Docker images for both Lambda functions |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| Hosting | Vercel |
| Routing | Path-based pagination (`/`, `/2`, `/3`, ...) |

---

## How the Ingest Pipeline Works

1. **Fetch** — Worker Lambda pulls entries from each RSS feed
2. **Resolve** — Google News redirect URLs are followed to get the real article URL
3. **Deduplicate** — Articles are matched by normalized URL and RSS entry GUID; already-seen articles are skipped
4. **Extract** — Full article HTML is fetched and cleaned (targets semantic HTML containers, detects cookie walls)
5. **Summarize** — New articles are summarized in 3 sentences via `gpt-4o-mini`
6. **Embed** — A 1536-dimension vector is generated via `text-embedding-3-small` for future semantic clustering
7. **Store** — Article, summary, and embedding are saved to PostgreSQL

---

## Database Schema

```
pages           — one row per unique article URL
page_versions   — one row per fetch, stores extracted text, summary, and embedding
stories         — AI-grouped clusters of articles (future feature)
story_articles  — links articles to stories
story_angles    — named sub-facets within a story (future feature)
coverage_reports — per-run media coverage analysis (future feature)
```

---

## RSS Sources

| Source | Type |
|---|---|
| Google News | Aggregator |
| AP News | Wire |
| The Guardian | Legacy |
| NPR | Legacy |
| BBC World | Legacy |
| Politico | Legacy |
| Al Jazeera | Independent |
| The Intercept | Independent |
| ProPublica | Independent/Investigative |

---

## Local Development

**Prerequisites:** Docker, Python 3.10+, Node.js 18+

```bash
# Clone the repo
git clone https://github.com/Reid910/InternetState.git
cd InternetState

# Add environment variables
cp .env.example .env
# Fill in OPENAI_API_KEY and DATABASE_URL

# Start Postgres locally
docker compose up postgres -d

# Run the worker once
cd worker && python main.py

# Start the API
cd api && uvicorn main:app --reload

# Start the frontend
cd frontend && npm install && npm run dev
```

---

## Deployment

The full stack is deployed via Docker container images on AWS Lambda.

```bash
# Build and push worker to ECR
docker buildx build --platform linux/amd64 --provenance=false \
  -f worker/Dockerfile.lambda \
  -t <ecr-repo>/internet-state-worker:latest --push ./worker

# Build and push API to ECR
docker buildx build --platform linux/amd64 --provenance=false \
  -f api/Dockerfile.lambda \
  -t <ecr-repo>/internet-state-api:latest --push ./api

# Frontend deploys automatically via Vercel on push to main
```

---

## Cost

| Service | Monthly Cost |
|---|---|
| AWS Lambda, EventBridge, API Gateway, ECR | ~$0 (free tier) |
| Neon PostgreSQL | $0 (free tier) |
| OpenAI API (summaries + embeddings) | ~$0.25 |
| Vercel | $0 (free tier) |
| **Total** | **~$0.25/month** |

---

## Roadmap

- **Story clustering** — group articles about the same event using embedding cosine similarity
- **Multi-source comparison** — show how different outlets covered the same story
- **Search** — full-text and semantic search across the article archive
- **Summary styles** — bullet points, ELI5, detailed breakdown
