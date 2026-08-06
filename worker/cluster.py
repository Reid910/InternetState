import numpy as np
from openai import OpenAI
from config import OPENAI_API_KEY

_openai = OpenAI(api_key=OPENAI_API_KEY)

SIMILARITY_THRESHOLD = 0.25  # cosine distance — tune this
MIN_ARTICLES_FOR_STORY = 2   # don't create a story from a single article


def _parse_embedding(raw) -> np.ndarray:
    if isinstance(raw, (list, np.ndarray)):
        return np.array(raw, dtype=np.float32)
    # psycopg2 returns vectors as strings like '[0.1,0.2,...]'
    return np.array(raw.strip("[]").split(","), dtype=np.float32)


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 1.0
    return float(1.0 - np.dot(a, b) / denom)


def _generate_story(articles: list[dict]) -> tuple[str, str]:
    """Ask GPT for a headline and 2-sentence summary given a list of article titles/summaries."""
    lines = []
    for a in articles[:8]:
        title = a.get("title") or ""
        summary = a.get("summary") or ""
        lines.append(f"- {title}: {summary[:200]}")
    prompt = (
        "The following news articles all cover the same story. "
        "Write a single neutral headline (max 12 words) and a 2-sentence summary of what happened. "
        "Respond in this exact format:\n"
        "HEADLINE: <headline>\n"
        "SUMMARY: <summary>\n\n"
        + "\n".join(lines)
    )
    resp = _openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
    )
    text = resp.choices[0].message.content.strip()
    headline, summary = "", ""
    for line in text.splitlines():
        if line.startswith("HEADLINE:"):
            headline = line.removeprefix("HEADLINE:").strip()
        elif line.startswith("SUMMARY:"):
            summary = line.removeprefix("SUMMARY:").strip()
    return headline or "Untitled Story", summary


def cluster_articles(conn, window_minutes: int = 90):
    """
    window_minutes: how far back to look for unassigned articles.
    Should be slightly larger than the EventBridge cadence so no
    articles are missed, but small enough to avoid re-pulling the
    full historical backlog on every run.
    """
    cur = conn.cursor()

    # --- Load unassigned articles with embeddings ---
    # Time-bounded so articles that never cluster don't re-transfer
    # their embeddings on every subsequent run indefinitely.
    cur.execute("""
        SELECT p.id, p.title, pv.summary, pv.embedding
        FROM pages p
        JOIN (
            SELECT DISTINCT ON (page_id) page_id, summary, embedding, fetched_at
            FROM page_versions
            WHERE ingest_status = 'full'
              AND embedding IS NOT NULL
              AND fetched_at > NOW() - INTERVAL '%s minutes'
            ORDER BY page_id, fetched_at DESC
        ) pv ON pv.page_id = p.id
        WHERE p.id NOT IN (SELECT page_id FROM story_articles)
        ORDER BY pv.fetched_at DESC
        LIMIT 500
    """ % window_minutes)
    unassigned = [
        {"id": r[0], "title": r[1], "summary": r[2], "embedding": _parse_embedding(r[3])}
        for r in cur.fetchall()
    ]

    emb_bytes = len(unassigned) * 1536 * 4
    print(f"[cluster] {len(unassigned)} unassigned articles (~{emb_bytes // 1024}KB embedding transfer)")

    if not unassigned:
        cur.close()
        return

    # --- Load recent story centroids (last 7 days only) ---
    # Avoids pulling all historical story embeddings on every run.
    cur.execute("""
        SELECT id, embedding FROM stories
        WHERE embedding IS NOT NULL
          AND updated_at > NOW() - INTERVAL '7 days'
    """)
    stories = [
        {"id": r[0], "centroid": _parse_embedding(r[1])}
        for r in cur.fetchall()
    ]
    print(f"[cluster] {len(stories)} active stories loaded (~{len(stories) * 1536 * 4 // 1024}KB)")

    still_unassigned = []

    for article in unassigned:
        emb = article["embedding"]
        best_story_id = None
        best_dist = SIMILARITY_THRESHOLD

        for story in stories:
            dist = _cosine_distance(emb, story["centroid"])
            if dist < best_dist:
                best_dist = dist
                best_story_id = story["id"]

        if best_story_id is not None:
            cur.execute(
                "INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (best_story_id, article["id"]),
            )
            # Update centroid: fetch current centroid and article count, recompute average
            cur.execute(
                "SELECT embedding, article_count FROM stories WHERE id = %s",
                (best_story_id,)
            )
            row = cur.fetchone()
            old_centroid = _parse_embedding(row[0])
            old_count = row[1] or 1
            new_count = old_count + 1
            new_centroid = ((old_centroid * old_count) + emb) / new_count
            cur.execute(
                "UPDATE stories SET embedding = %s, article_count = %s, updated_at = NOW() WHERE id = %s",
                (new_centroid.tolist(), new_count, best_story_id),
            )
            # Update the in-memory centroid so subsequent articles in this batch use it
            for s in stories:
                if s["id"] == best_story_id:
                    s["centroid"] = new_centroid
            conn.commit()
        else:
            still_unassigned.append(article)

    print(f"[cluster] {len(unassigned) - len(still_unassigned)} assigned to existing stories, {len(still_unassigned)} remaining")

    # --- Group remaining articles with each other ---
    used = set()
    new_clusters = []

    for i, a in enumerate(still_unassigned):
        if i in used:
            continue
        cluster = [a]
        used.add(i)
        for j, b in enumerate(still_unassigned):
            if j <= i or j in used:
                continue
            if _cosine_distance(a["embedding"], b["embedding"]) < SIMILARITY_THRESHOLD:
                cluster.append(b)
                used.add(j)
        if len(cluster) >= MIN_ARTICLES_FOR_STORY:
            new_clusters.append(cluster)

    print(f"[cluster] {len(new_clusters)} new stories to create")

    for cluster in new_clusters:
        headline, summary = _generate_story(cluster)
        centroid = np.mean([a["embedding"] for a in cluster], axis=0)

        cur.execute("""
            INSERT INTO stories (headline, summary, embedding, article_count, last_seen, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
            RETURNING id
        """, (headline, summary, centroid.tolist(), len(cluster)))
        story_id = cur.fetchone()[0]

        for a in cluster:
            cur.execute(
                "INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (story_id, a["id"]),
            )

        stories.append({"id": story_id, "centroid": centroid})
        conn.commit()
        print(f"  [new story] {headline} ({len(cluster)} articles)")

    cur.close()
