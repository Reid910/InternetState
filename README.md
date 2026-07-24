# Internet State

A serverless news intelligence platform that ingests articles from RSS feeds across the web, summarizes them with AI, clusters related articles into stories using vector embeddings, and serves everything through a live-updating public feed.

**Live site:** [internet-state-roan.vercel.app](https://internet-state-roan.vercel.app)

---

## Engineering Highlights

A few decisions in this codebase worth calling out:

- **Story clustering is incremental, not batch.** Rather than re-clustering all articles on every run, the worker compares only new articles against existing story centroids using cosine similarity. When an article joins a story, the centroid is updated as a running weighted average of its member embeddings — no reprocessing of old data, no full-table scans. New clusters are only promoted to stories once they reach a minimum article threshold, which filters out one-off articles that don't represent a real ongoing story.

- **Consent walls are detected by heuristic, not URL blocklist.** Many news sites serve a cookie consent page instead of article content when requests lack browser cookies. The extracted text passes word-count checks but is garbage. Rather than maintaining a blocklist of domains, the worker checks extracted text for 2+ privacy-related phrases (GDPR, cookie policy, etc.) combined with a short word count — a signal reliable enough to catch consent walls across any domain without site-specific configuration.

- **Google News URLs require two resolution strategies.** Google News RSS feeds wrap every link in a redirect. Following HTTP redirects works most of the time, but some responses stay on `news.google.com` even after redirecting. The fallback fetches a small HTML chunk from the redirect URL and sniffs `og:url` or the canonical link tag. Without this two-pass approach, a significant share of articles from the largest feed would silently fail to resolve.

- **The API Lambda cold start broke when a new package was added.** The original `Dockerfile` used `python:3.11-slim` with `CMD ["uvicorn", "main:app", "--reload"]` — which worked until the `openai` package was added and pushed initialization past Lambda's cold start timeout. The fix was switching to `public.ecr.aws/lambda/python:3.11` with `CMD ["main.handler"]`. Lambda container images must use the AWS Lambda runtime base image, not a generic Python image running a server.

- **In-memory TTL caching cuts database transfer without infrastructure overhead.** Lambda instances persist in memory between warm invocations. The API exploits this by caching query results in a module-level dict keyed by endpoint + params, with a 5-minute TTL. This reduced Neon network transfer by ~80–90% without adding Redis or any external cache layer — important given Neon's free tier transfer limits.

- **The frontend never fetches data on the client.** All API calls happen in Next.js server components with `next: { revalidate: 300 }`, so pages are rendered server-side and cached at the edge. Client components handle only interactivity (theme toggle, search form, expandable source lists). This means the page is fully rendered on first load with no loading states, no layout shift, and no client-side API keys.

---

## How It Works

### Ingest pipeline (runs every 15 minutes)

1. **Fetch** — Worker Lambda pulls entries from each RSS feed
2. **Resolve** — Google News redirect URLs are followed using a two-pass strategy (HTTP redirect + `og:url` sniffing)
3. **Deduplicate** — Articles are matched by normalized URL and RSS entry GUID; already-seen articles are skipped
4. **Extract** — Full article HTML is fetched and cleaned; consent walls are detected and rejected
5. **Summarize** — New articles are summarized in 3 sentences via `gpt-4o-mini`
6. **Embed** — A 1536-dimension vector is generated via `text-embedding-3-small`
7. **Store** — Article, summary, and embedding are saved to PostgreSQL
8. **Cluster** — New articles are compared against existing story centroids using cosine similarity; matching articles extend existing stories, unmatched articles form new ones; GPT generates a headline and summary for each new story

### API

FastAPI on AWS Lambda, behind API Gateway. Endpoints for stories, articles, sources, stats, and search. Results are cached in Lambda memory with a 5-minute TTL. Search supports both full-text (PostgreSQL `tsvector`) and semantic (pgvector cosine similarity) modes.

### Frontend

Next.js App Router on Vercel. Server components fetch and render data; client components handle the search form, theme toggle, and expandable story cards. Dark/light mode uses CSS custom properties with a system-preference default and localStorage persistence.

---

## Architecture

```
RSS Feeds
   ↓
AWS EventBridge Scheduler  — fires every 15 minutes
   ↓
AWS Lambda (worker)        — fetches, deduplicates, summarizes, embeds, clusters
   ↓
OpenAI API                 — gpt-4o-mini (summaries) + text-embedding-3-small (vectors)
   ↓
Neon PostgreSQL + pgvector — articles, summaries, embeddings, stories
   ↓
AWS Lambda + API Gateway   — FastAPI REST API with in-memory TTL caching
   ↓
Vercel (Next.js)           — server-rendered frontend, edge-cached
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Ingest worker | Python, feedparser, BeautifulSoup |
| AI summarization | OpenAI gpt-4o-mini |
| Vector embeddings | OpenAI text-embedding-3-small (1536-dim) |
| Story clustering | pgvector cosine similarity + incremental centroid averaging |
| Database | PostgreSQL + pgvector (Neon) |
| REST API | FastAPI, Mangum (Lambda adapter) |
| Infrastructure | AWS Lambda, EventBridge, API Gateway, ECR |
| Frontend | Next.js (App Router), Vercel |
| Search | PostgreSQL tsvector (full-text) + pgvector (semantic) |

---

## Known Limitations

- **In-memory cache only** — Cache is lost on cold starts and not shared between concurrent Lambda instances. A persistent layer (Redis, DynamoDB) would be needed at higher traffic.
- **Single-threaded ingest** — Articles are fetched and processed sequentially. A queue-based parallel approach would be significantly faster on large feed volumes.
- **No SEO files** — No `robots.txt`, `sitemap.xml`, or `og:image` meta tags.
- **Story clustering is eventual** — Stories only appear after an ingest cycle completes. A freshly deployed instance shows 0 stories until the first worker run finishes.

---

## What I Learned

**Lambda needs its own base image.** A generic `python:3.11-slim` image running uvicorn worked in local Docker but silently broke at scale when a heavier package pushed cold start initialization past Lambda's timeout. Switching to the AWS Lambda base image with the correct handler entrypoint fixed it — and revealed that the previous setup had only appeared to work due to cached warm instances.

**Consent walls are a data quality problem, not a networking problem.** Early versions produced nonsense summaries that turned out to be GPT summarizing cookie consent pages. The fix wasn't to avoid those sites — it was to detect and reject consent-wall content after extraction, which keeps the pipeline working even when site behavior changes.

**Vector databases make clustering practical at small scale.** Using pgvector meant no separate ML infrastructure — similarity search and storage live in the same Postgres database as everything else. Incremental centroid updates kept the clustering step fast without ever needing to reprocess the full article history.

---

## Tests

```bash
# Worker unit tests (24 tests — no network, no DB, no OpenAI)
cd worker && python -m pytest test_ingest.py -v

# API unit tests (10 tests — all external calls mocked)
cd api && python -m pytest test_api.py -v
```

---

## Local Development

**Prerequisites:** Docker, Python 3.10+, Node.js 18+

```bash
git clone https://github.com/Reid910/internet-state.git
cd internet-state

cp .env.example .env
# Fill in OPENAI_API_KEY and DATABASE_URL

docker compose up postgres -d

cd worker && python main.py   # run ingest once
cd api && uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

---

## Deployment

```bash
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com

docker buildx build --platform linux/amd64 --provenance=false \
  -t <ecr-repo>/internet-state-api:latest --push ./api

aws lambda update-function-code \
  --function-name internet-state-api \
  --image-uri <ecr-repo>/internet-state-api:latest

# Frontend deploys automatically via Vercel on push to main
```
