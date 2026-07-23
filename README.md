# Internet State

A serverless news intelligence platform that automatically ingests articles from RSS feeds, summarizes them with AI, clusters related articles into stories, and displays everything in a live-updating web feed.

**Live site:** [internet-state-roan.vercel.app](https://internet-state-roan.vercel.app)

---

## What It Does

- Fetches articles from RSS news sources every 15 minutes
- Deduplicates articles by URL and GUID
- Summarizes each new article using GPT-4o-mini
- Generates vector embeddings and clusters related articles into stories using cosine similarity
- Serves articles and stories through a REST API with caching, search, filtering, and pagination
- Displays a live feed at a public URL with dark/light mode, inline search, and story detail pages

---

## Architecture

```
RSS Feeds
   ↓
AWS EventBridge Scheduler  — fires every 15 minutes
   ↓
AWS Lambda (worker)        — fetches, extracts, deduplicates, summarizes, clusters
   ↓
OpenAI API                 — gpt-4o-mini (summaries) + text-embedding-3-small (vectors)
   ↓
Neon PostgreSQL + pgvector — stores articles, summaries, embeddings, and stories
   ↓
AWS Lambda + API Gateway   — FastAPI REST API with in-memory TTL caching
   ↓
Vercel (Next.js)           — server-rendered frontend with 5-minute cache
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Ingest worker | Python, feedparser, BeautifulSoup |
| Story clustering | pgvector cosine similarity + incremental centroid averaging |
| AI summarization | OpenAI gpt-4o-mini |
| Vector embeddings | OpenAI text-embedding-3-small (1536-dim) |
| Database | PostgreSQL + pgvector (Neon) |
| REST API | Python, FastAPI, Mangum |

### AWS Services
| Service | Role |
|---|---|
| **Lambda** | Runs the ingest worker and API |
| **EventBridge Scheduler** | Triggers the worker on a cron schedule |
| **API Gateway** | HTTP endpoint in front of the FastAPI Lambda |
| **ECR** | Stores Docker images for both Lambda functions |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js (App Router, server components) |
| Hosting | Vercel |
| Search | PostgreSQL full-text search (tsvector) + semantic (pgvector) |

---

## How the Ingest Pipeline Works

1. **Fetch** — Worker Lambda pulls entries from each RSS feed
2. **Resolve** — Google News redirect URLs are followed to get the real article URL
3. **Deduplicate** — Articles are matched by normalized URL and RSS entry GUID; already-seen articles are skipped
4. **Extract** — Full article HTML is fetched and cleaned (targets semantic HTML containers, detects cookie walls)
5. **Summarize** — New articles are summarized in 3 sentences via `gpt-4o-mini`
6. **Embed** — A 1536-dimension vector is generated via `text-embedding-3-small`
7. **Store** — Article, summary, and embedding are saved to PostgreSQL
8. **Cluster** — New articles are compared against existing story centroids; similar articles are grouped into stories and a headline + summary is generated for each cluster

---

## Database Schema

```
pages           — one row per unique article URL
page_versions   — one row per fetch, stores summary and embedding
stories         — AI-grouped clusters of related articles
story_articles  — links articles to stories
```

---

## RSS Sources

| Source | Type |
|---|---|
| Google News | Aggregator |
| AP News | Wire |
| The Guardian | News |
| NPR | News |
| BBC World | News |
| Politico | News |
| Al Jazeera | News |
| The Intercept | News |
| ProPublica | Investigative |

---

## What I Learned

**Google News redirect quirks** — Google News wraps every article link in a redirect URL. Simply following HTTP redirects works most of the time, but some responses stay on `news.google.com` even after following. The fallback is to fetch a small HTML chunk and sniff `og:url` or the canonical link tag. Without this, a large percentage of articles from the biggest feed would fail to resolve.

**Consent walls break text extraction** — Many news sites serve a cookie consent page instead of article content when requests come from certain IPs or lack browser cookies. The extracted text passes length checks but is garbage. The fix was a phrase-matching heuristic: if the extracted text contains 2+ consent-related phrases *and* is under 400 words, it's rejected as a consent wall. This eliminated a class of nonsense summaries.

**Lambda cold starts need the right base image** — The API was originally built on `python:3.11-slim` with `CMD ["uvicorn", "main:app"]`. This worked until the `openai` package was added — the heavier import pushed initialization past Lambda's cold start timeout, breaking every endpoint. Switching to `public.ecr.aws/lambda/python:3.11` with `CMD ["main.handler"]` fixed it. Lambda container images must use the AWS Lambda runtime, not a generic server.

---

## Known Limitations

- **No automated tests** — The codebase has no unit or integration tests. Adding at minimum worker deduplication tests and API response tests is the next priority.
- **In-memory cache only** — The API caches results in Lambda memory with a 5-minute TTL. Cache is lost on cold starts and not shared between concurrent Lambda instances.
- **Single-threaded ingest** — Articles are fetched and processed one at a time. On large feeds this is slow; a queue-based parallel approach would be significantly faster.
- **No SEO files** — No `robots.txt`, `sitemap.xml`, or `og:image` meta tags. The site is not optimized for crawling or social sharing.
- **Story clustering is eventual** — Stories only appear after an ingest cycle runs. A freshly deployed instance shows 0 stories until the first worker invocation completes.

---

## Local Development

**Prerequisites:** Docker, Python 3.10+, Node.js 18+

```bash
# Clone the repo
git clone https://github.com/Reid910/internet-state.git
cd internet-state

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

Both Lambda functions are deployed as Docker container images on AWS.

```bash
# Login to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com

# Build and push API
docker buildx build --platform linux/amd64 --provenance=false \
  -t <ecr-repo>/internet-state-api:latest --push ./api

# Update Lambda
aws lambda update-function-code \
  --function-name internet-state-api \
  --image-uri <ecr-repo>/internet-state-api:latest

# Frontend deploys automatically via Vercel on push to main
```
